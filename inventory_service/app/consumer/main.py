from sqlmodel import SQLModel, Field, select, Session
from app import settings, inventory_pb2,db
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
import logging
import uuid
from uuid import UUID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



#  Used for data validation and table fields 
class Inventory(SQLModel, table=True):
    __tablename__ = "inventory"
    id: int | None = Field(default=None, primary_key=True)
    inventory_id: UUID = Field(default_factory=uuid.uuid4, index=True)
    product_id:UUID = Field(index=True)
    stock_level:int = Field(default=0,index=True)
    reserved_stock:int = Field(default=0,index=True)

# Retry utility
async def retry_async(func, retries=5, delay=2, *args, **kwargs):
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise

#  Functions to produce message based on topic name and message 
async def produce_message(topic, message):
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await retry_async(producer.start)
    try:
        await producer.send_and_wait(topic, message)
    finally:
        await producer.stop()

#  Function to handle get all inventorys request from producer side from where API is called to get all inventorys 
async def handle_get_all_inventorys():
    with Session(db.engine) as session:
        inventorys_list = session.exec(select(Inventory)).all()
        inventory_list_proto = inventory_pb2.ProductList()
        for inventory in inventorys_list:
            inventory_proto = inventory_pb2.Inventory(
                id=inventory.id,
                inventory_id=str(inventory.inventory_id),
                name=inventory.name,
                description=inventory.description,
                price=inventory.price,
                is_available=inventory.is_available,
            )
            inventory_list_proto.inventorys.append(inventory_proto)
        serialized_inventory_list = inventory_list_proto.SerializeToString()
        await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory_list)
        logger.info(f"List of inventorys sent back from database: {inventory_list_proto}")


#  Function to handle get inventory request from producer side from where API is called to get a  inventorys 
async def handle_get_inventory(inventory_id):
    with Session(db.engine) as session:
        inventory = session.exec(select(Inventory).where(Inventory.inventory_id == inventory_id)).first()
        if inventory:
            inventory_proto = inventory_pb2.Inventory(
                id=inventory.id,
                inventory_id=str(inventory.inventory_id),
                name=inventory.name,
                description=inventory.description,
                price=inventory.price,
                is_available=inventory.is_available,
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)
            logger.info(f"Inventory sent back from database: {inventory_proto}")
        else:
            inventory_proto = inventory_pb2.Inventory(
                error_message=f"No Inventory with inventory_id: {inventory_id} found!",
                http_status_code=400
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)


#  Function to handle add  inventory request from producer side from where API is called to add inventory to database 
async def handle_add_inventory(new_msg):
    with Session(db.engine) as session:
        inventory = session.exec(select(Inventory).where(Inventory.product_id == new_msg.product_id)).first()
        logger.info(f"Get back product detail from database based on product_id: {inventory}")        
        #  write logic whatever you want to do with the fields of table 
        if inventory:
            inventory.stock_level +=new_msg.add_stock_level
            session.add(inventory)
            session.commit()
            session.refresh(inventory)
            logger.info(f"Get back product detail from database after adding stock level: {inventory}")  
            #  agin update to database 
            inventory_proto = inventory_pb2.Inventory(
                id=inventory.id,
                inventory_id=str(inventory.inventory_id),
                product_id = str(inventory.product_id),
                stock_level=inventory.stock_level,
                reserved_stock=inventory.reserved_stock,
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)
            logger.info(f"Inventory sent back from database: {inventory_proto}")
        else:
            inventory_proto = inventory_pb2.Inventory(
                error_message=f"No Product with product_id: {new_msg.product_id} found!",
                http_status_code=404
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)


#  Function to handle reduce inventory request from producer side from where API is called to reduce inventory to database 
async def handle_reduce_inventory(new_msg):
    with Session(db.engine) as session:
        inventory = session.exec(select(Inventory).where(Inventory.product_id == new_msg.product_id)).first()
        logger.info(f"Get back product detail from database based on product_id: {inventory}")        
        #  write logic whatever you want to do with the fields of table 
        if inventory:
            # inventory.stock_level -= new_msg.reduce_stock_level
            inventory.stock_level = inventory.stock_level  - new_msg.reduce_stock_level
            session.add(inventory)
            session.commit()
            session.refresh(inventory)
            logger.info(f"Get back product detail from database after reducing stock level: {inventory}")  
            inventory_proto = inventory_pb2.Inventory(
                id=inventory.id,
                inventory_id=str(inventory.inventory_id),
                product_id = str(inventory.product_id),
                stock_level=inventory.stock_level,
                reserved_stock=inventory.reserved_stock,
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)
            logger.info(f"Inventory sent back from database: {inventory_proto}")
        else:
            inventory_proto = inventory_pb2.Inventory(
                error_message=f"No Product with product_id: {new_msg.product_id} found!",
                http_status_code=404
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)




#  Function to handle update inventory request from producer side from where API is called to update inventory to database 
async def handle_update_inventory(new_msg):
    with Session(db.engine) as session:
        inventory = session.exec(select(Inventory).where(Inventory.inventory_id == new_msg.inventory_id)).first()
        if inventory:
            inventory.name = new_msg.name
            inventory.description = new_msg.description
            inventory.price = new_msg.price
            inventory.is_available = new_msg.is_available
            session.add(inventory)
            session.commit()
            session.refresh(inventory)
            inventory_proto = inventory_pb2.Inventory(
                id=inventory.id,
                inventory_id=str(inventory.inventory_id),
                product_id = str(inventory.product_id),
                stock_level=inventory.stock_level,
                reserved_stock=inventory.reserved_stock,
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)
            logger.info(f"Inventory updated in database and sent back: {inventory_proto}")
        else:
            inventory_proto = inventory_pb2.Inventory(
                error_message=f"No Inventory with inventory_id: {new_msg.inventory_id} found!",
                http_status_code=400
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)


#  Function to handle delete inventory request from producer side from where API is called to delete inventory from database 
async def handle_delete_inventory(inventory_id):
    with Session(db.engine) as session:
        inventory = session.exec(select(Inventory).where(Inventory.inventory_id == inventory_id)).first()
        if inventory:
            session.delete(inventory)
            session.commit()
            inventory_proto = inventory_pb2.Inventory(
                error_message=f"Inventory with inventory_id: {inventory_id} deleted!",
                http_status_code=200
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)
            logger.info(f"Inventory deleted and confirmation sent back: {inventory_proto}")
        else:
            inventory_proto = inventory_pb2.Inventory(
                error_message=f"No Inventory with inventory_id: {inventory_id} found!",
                http_status_code=400
            )
            serialized_inventory = inventory_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_inventory)


#  Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs 
async def consume_message_from_producer_of_inventory():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_INVENTORY,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY,
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = inventory_pb2.Inventory()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message: {new_msg}")

            if new_msg.option == inventory_pb2.SelectOption.GET_ALL:
                await handle_get_all_inventorys()
            elif new_msg.option == inventory_pb2.SelectOption.GET:
                await handle_get_inventory(new_msg.inventory_id)
            elif new_msg.option == inventory_pb2.SelectOption.ADD:
                await handle_add_inventory(new_msg)
            elif new_msg.option == inventory_pb2.SelectOption.REDUCE:
                await handle_reduce_inventory(new_msg)
            elif new_msg.option == inventory_pb2.SelectOption.DELETE:
                await handle_delete_inventory(new_msg.inventory_id)
            else:
                logger.warning(f"Unknown option received: {new_msg.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()


#  Function to consume message from the create product API on the producer side of ptoduct service  and update product with id in inventory service 
async def consume_message_from_create_product_of_product():
    consumer = AIOKafkaConsumer(
        f"{(settings.KAFKA_TOPIC_GET_FROM_PRODUCT).strip()}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{(settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT)}",
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"Received message: {msg}")
            new_msg = inventory_pb2.Product()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received msg.value: {new_msg}")

            inventory = Inventory(
                product_id = uuid.UUID(new_msg.product_id)
            )
            with Session(db.engine) as session:
                session.add(inventory)
                session.commit()
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()