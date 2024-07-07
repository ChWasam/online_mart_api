from sqlmodel import SQLModel, Field, create_engine, select, Session
from app import settings, product_pb2,db
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
import logging
import uuid
from uuid import UUID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



#  Used for data validation and table fields 
class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: UUID = Field(default_factory=uuid.uuid4, index=True)
    name: str = Field(index=True)
    description: str = Field(index=True)
    price: float = Field(index=True)
    is_available: bool = Field(default=True)

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

#  Function to handle get all products request from producer side from where API is called to get all products 
async def handle_get_all_products():
    with Session(db.engine) as session:
        products_list = session.exec(select(Product)).all()
        product_list_proto = product_pb2.ProductList()
        for product in products_list:
            product_proto = product_pb2.Product(
                id=product.id,
                product_id=str(product.product_id),
                name=product.name,
                description=product.description,
                price=product.price,
                is_available=product.is_available,
            )
            product_list_proto.products.append(product_proto)
        serialized_product_list = product_list_proto.SerializeToString()
        await produce_message(settings.KAFKA_TOPIC_GET, serialized_product_list)
        logger.info(f"List of products sent back from database: {product_list_proto}")


#  Function to handle get product request from producer side from where API is called to get a  products 
async def handle_get_product(product_id):
    with Session(db.engine) as session:
        product = session.exec(select(Product).where(Product.product_id == product_id)).first()
        if product:
            product_proto = product_pb2.Product(
                id=product.id,
                product_id=str(product.product_id),
                name=product.name,
                description=product.description,
                price=product.price,
                is_available=product.is_available,
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)
            logger.info(f"Product sent back from database: {product_proto}")
        else:
            product_proto = product_pb2.Product(
                error_message=f"No Product with product_id: {product_id} found!",
                status=400
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)


#  Function to handle add product request from producer side from where API is called to add product to database 
async def handle_create_product(new_msg):
    product = Product(
        name=new_msg.name,
        description=new_msg.description,
        price=new_msg.price,
        is_available=new_msg.is_available
    )
    with Session(db.engine) as session:
        session.add(product)
        session.commit()
    logger.info(f"Product added to database: {product}")


#  Function to handle update product request from producer side from where API is called to update product to database 
async def handle_update_product(new_msg):
    with Session(db.engine) as session:
        product = session.exec(select(Product).where(Product.product_id == new_msg.product_id)).first()
        if product:
            product.name = new_msg.name
            product.description = new_msg.description
            product.price = new_msg.price
            product.is_available = new_msg.is_available
            session.add(product)
            session.commit()
            session.refresh(product)
            product_proto = product_pb2.Product(
                id=product.id,
                product_id=str(product.product_id),
                name=product.name,
                description=product.description,
                price=product.price,
                is_available=product.is_available,
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)
            logger.info(f"Product updated in database and sent back: {product_proto}")
        else:
            product_proto = product_pb2.Product(
                error_message=f"No Product with product_id: {new_msg.product_id} found!",
                status=400
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)


#  Function to handle delete product request from producer side from where API is called to delete product from database 
async def handle_delete_product(product_id):
    with Session(db.engine) as session:
        product = session.exec(select(Product).where(Product.product_id == product_id)).first()
        if product:
            session.delete(product)
            session.commit()
            product_proto = product_pb2.Product(
                error_message=f"Product with product_id: {product_id} deleted!",
                status=200
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)
            logger.info(f"Product deleted and confirmation sent back: {product_proto}")
        else:
            product_proto = product_pb2.Product(
                error_message=f"No Product with product_id: {product_id} found!",
                status=400
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)


#  Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs 
async def consume_message_request():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT,
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = product_pb2.Product()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message: {new_msg}")

            if new_msg.option == product_pb2.SelectOption.GET_ALL:
                await handle_get_all_products()
            elif new_msg.option == product_pb2.SelectOption.GET:
                await handle_get_product(new_msg.product_id)
            elif new_msg.option == product_pb2.SelectOption.CREATE:
                await handle_create_product(new_msg)
            elif new_msg.option == product_pb2.SelectOption.UPDATE:
                await handle_update_product(new_msg)
            elif new_msg.option == product_pb2.SelectOption.DELETE:
                await handle_delete_product(new_msg.product_id)
            else:
                logger.warning(f"Unknown option received: {new_msg.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()
