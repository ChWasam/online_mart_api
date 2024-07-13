from sqlmodel import SQLModel,Field,create_engine,select, Session
from google.protobuf.json_format import MessageToDict
from fastapi import FastAPI,Depends,HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
from aiokafka import AIOKafkaProducer , AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from app import inventory_pb2
from app import settings
from app import db 
from app.consumer import main
import uuid 
from uuid import UUID 
import asyncio
import psycopg
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Retry utility
async def retry_async(func, retries=5, delay=2, *args, **kwargs):
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise


# Creating topic from code 
async def create_topic ():
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}"
    )
    await retry_async(admin_client.start)
    topic_list = [
        NewTopic(name=f"{settings.KAFKA_TOPIC_INVENTORY}", num_partitions=2, replication_factor=1),
        NewTopic(name=f"{settings.KAFKA_TOPIC_GET}", num_partitions=2, replication_factor=1)
    ]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only= False)
    except Exception as e:
        logger.error ( "Error creating topics:: {e}")
    finally:
        await admin_client.close()

#  Function to consume list of all inventorys from kafkatopic
async def consume_message_response_get_all():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer : {msg}")
            try:
                new_msg = inventory_pb2.InventoryList()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()

#  Function to consume all messages other than list of all inventorys from kafkatopic
async def consume_message_response():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = inventory_pb2.Inventory()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()


# Pydantic dataValidation 
class Inventory(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    inventory_id: UUID = Field(default_factory=uuid.uuid4, index=True)
    product_id:UUID = Field(index=True)
    stock_level:int = Field(index=True)
    reserved_stock:int = Field(index=True)


class InventoryPost(SQLModel):
    update_stock_level:int = Field(index=True)


#  Function to produce message. I will work as a dependency injection for APIs
async def produce_message():
    producer = AIOKafkaProducer(bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}")
    await retry_async(producer.start)
    try:
        yield producer
    finally:
        await producer.stop()


#  It contains all the instructions that will run when the application will start
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_table()
    await create_topic()
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(main.consume_message_from_producer_of_inventory())
    task2 = loop.create_task(main.consume_message_from_create_product_of_product())
    task3 = loop.create_task(main.consume_message_for_inventory_check())
    try:
        yield
    finally:
        for task in [task1, task2,task3]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass



# Home Endpoint
app:FastAPI = FastAPI(lifespan=lifespan )
@app.get("/")
async def read_root():
    return {"Hello":"Inventory Service"}

# Endpoint to get all the inventorys
@app.get("/inventory", response_model= list[Inventory])
async def get_all_inventories(producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    inventory_proto = inventory_pb2.Inventory(option = inventory_pb2.SelectOption.GET_ALL)
    serialized_inventory = inventory_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC_INVENTORY}",serialized_inventory)
    inventory_list_proto = await consume_message_response_get_all()

    inventory_list = [
        {
                "id":inventory.id,
                "inventory_id":str(inventory.inventory_id),
                "product_id" : str(inventory.product_id),
                "stock_level":inventory.stock_level,
                "reserved_stock":inventory.reserved_stock,

        }
        for inventory in inventory_list_proto.inventories
    ]
    return inventory_list


#  Endpoint to get the single inventory based on endpoint 
@app.get("/inventory/{inventory_id}", response_model=dict)
async def get_a_inventory(inventory_id:UUID, producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    inventory_proto = inventory_pb2.Inventory(inventory_id =str(inventory_id),  option = inventory_pb2.SelectOption.GET)
    serialized_inventory = inventory_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC_INVENTORY}",serialized_inventory)
    inventory_proto = await consume_message_response()
    if inventory_proto.error_message or inventory_proto.http_status_code :
        raise HTTPException(status_code=inventory_proto.http_status_code, detail=inventory_proto.error_message)
    else:
        return         {
                "id":inventory_proto.id,
                "inventory_id":str(inventory_proto.inventory_id),
                "product_id" : str(inventory_proto.product_id),
                "stock_level":inventory_proto.stock_level,
                "reserved_stock":inventory_proto.reserved_stock,

        }


#  Endpoint to add inventory to database 
@app.put("/inventory/{product_id}/add", response_model=dict)
async  def add_inventory (product_id:UUID, add_stock_level:InventoryPost , producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    inventory_proto = inventory_pb2.Inventory(
        product_id = str(product_id),
        add_stock_level = add_stock_level.update_stock_level,
        option = inventory_pb2.SelectOption.ADD)
    serialized_inventory = inventory_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC_INVENTORY}",serialized_inventory)
    inventory_proto = await consume_message_response()
    if inventory_proto.error_message or inventory_proto.http_status_code :
        raise HTTPException(status_code=inventory_proto.http_status_code, detail=inventory_proto.error_message)
    else:
        return {
                "id":inventory_proto.id,
                "inventory_id":str(inventory_proto.inventory_id),
                "product_id" : str(inventory_proto.product_id),
                "stock_level":inventory_proto.stock_level,
                "reserved_stock":inventory_proto.reserved_stock,
        }


#  Endpoint to reduce inventory from database 
@app.put("/inventory/{product_id}/reduce", response_model=dict)
async  def reduce_inventory (product_id:UUID, reduce_stock_level:InventoryPost , producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    inventory_proto = inventory_pb2.Inventory(
        product_id = str(product_id),
        reduce_stock_level = reduce_stock_level.update_stock_level,
        option = inventory_pb2.SelectOption.REDUCE)
    logger.info(f"Initial detail send to consumer for reducing stock option {inventory_proto}")    
    serialized_inventory = inventory_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC_INVENTORY}",serialized_inventory)
    inventory_proto = await consume_message_response()
    if inventory_proto.error_message or inventory_proto.http_status_code :
        raise HTTPException(status_code=inventory_proto.http_status_code, detail=inventory_proto.error_message)
    else:
        return {
                "id":inventory_proto.id,
                "inventory_id":str(inventory_proto.inventory_id),
                "product_id" : str(inventory_proto.product_id),
                "stock_level":inventory_proto.stock_level,
                "reserved_stock":inventory_proto.reserved_stock,
        }

#  Endpoint to delete inventory from database 
# @app.delete("/inventorys/{inventory_id}", response_model=dict)
# async  def delete_inventory (inventory_id:UUID, producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
#     inventory_proto = inventory_pb2.Inventory(inventory_id= str(inventory_id), option = inventory_pb2.SelectOption.DELETE)
#     serialized_inventory = inventory_proto.SerializeToString()
#     await producer.send_and_wait(f"{settings.KAFKA_TOPIC_INVENTORY}",serialized_inventory)
#     return {"Delete  Message": "Message Deleted"}




