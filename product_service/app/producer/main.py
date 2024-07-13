from sqlmodel import SQLModel,Field,create_engine,select, Session
from google.protobuf.json_format import MessageToDict
from fastapi import FastAPI,Depends,HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
from aiokafka import AIOKafkaProducer , AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from app import product_pb2
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
        NewTopic(name=f"{(settings.KAFKA_TOPIC).strip()}", num_partitions=2, replication_factor=1),
        NewTopic(name=f"{(settings.KAFKA_TOPIC_GET).strip()}", num_partitions=2, replication_factor=1)
    ]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only= False)
    except Exception as e:
        logger.error ( "Error creating topics:: {e}")
    finally:
        await admin_client.close()

#  Function to consume list of all products from kafkatopic
async def consume_message_response_get_all():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer : {msg}")
            try:
                new_msg = product_pb2.ProductList()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()

#  Function to consume all messages other than list of all products from kafkatopic
async def consume_message_response():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = product_pb2.Product()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()


# Pydantic dataValidation 
#  Product create, productupdate, productresponse 
class Product(SQLModel):
    id : int|None = Field(default = None , primary_key= True)
    product_id:UUID = Field(default_factory=uuid.uuid4, index=True)
    name:str = Field(index=True)
    description:str = Field(index=True)
    price:float= Field(index=True)
    is_available: bool = Field(default=False)

class ProductUpdateDelete(SQLModel):

    name:str = Field(index=True)
    description:str = Field(index=True)
    price:float= Field(index=True)
    is_available: bool = Field(default=False)





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
    task1 = loop.create_task(main.consume_message_request())
    task2 = loop.create_task(main.consume_message_for_stock_level_update())
    try:
        yield
    finally:
        for task in [task1,task2]:
            task.cancel()
            await task
            
# Home Endpoint
app:FastAPI = FastAPI(lifespan=lifespan )
@app.get("/")
async def read_root():
    return {"Hello":"Product Service"}

# Endpoint to get all the products
@app.get("/products", response_model= list[Product])
async def get_all_products(producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    product_proto = product_pb2.Product(option = product_pb2.SelectOption.GET_ALL)
    serialized_product = product_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_product)
    product_list_proto = await consume_message_response_get_all()

    product_list = [
        {
            "id":product.id,
            "product_id":str(product.product_id),
            "name":product.name,
            "description":product.description,
            "price":product.price,
            "is_available":product.is_available,

        }
        for product in product_list_proto.products
    ]
    return product_list


#  Endpoint to get the single product based on endpoint 
@app.get("/products/{product_id}", response_model=dict)
async def get_a_product(product_id:UUID, producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    product_proto = product_pb2.Product(product_id =str(product_id),  option = product_pb2.SelectOption.GET)
    serialized_product = product_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_product)
    product_proto = await consume_message_response()
    if product_proto.error_message or product_proto.http_status_code :
        raise HTTPException(status_code=product_proto.http_status_code, detail=product_proto.error_message)
    else:
        
        return MessageToDict(product_proto)

#  Endpoint to add product to database 
@app.post("/products", response_model=dict)
async  def add_product (product:ProductUpdateDelete , producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    product_proto = product_pb2.Product(name = product.name, description = product.description , price = product.price , is_available = product.is_available, option = product_pb2.SelectOption.CREATE)
    serialized_product = product_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_product)
    product_proto = await consume_message_response()
    if product_proto.error_message or product_proto.http_status_code :
        raise HTTPException(status_code=product_proto.http_status_code, detail=product_proto.error_message)
    else:
        product_return_from_db = {
            "id":product_proto.id,
            "product_id":str(product_proto.product_id),
            "name":product_proto.name,
            "description":product_proto.description,
            "price":product_proto.price,
            "is_available":product_proto.is_available,
        }
        return product_return_from_db
        # or
        # return MessageToDict(product_proto)



#  Endpoint to update product to database 
@app.put("/products/{product_id}", response_model = dict)
async  def update_product (product_id:UUID, product:ProductUpdateDelete , producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    product_proto = product_pb2.Product(product_id= str(product_id), name = product.name, description = product.description ,price = product.price , is_available = product.is_available, option = product_pb2.SelectOption.UPDATE)
    serialized_product = product_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_product)
    product_proto = await consume_message_response()
    if product_proto.error_message or product_proto.http_status_code :
        raise HTTPException(status_code=product_proto.http_status_code, detail=product_proto.error_message)
    else:
        return{"Updated Message": MessageToDict(product_proto)}


#  Endpoint to delete product from database 
@app.delete("/products/{product_id}", response_model=dict)
async  def delete_product (product_id:UUID, producer:Annotated[AIOKafkaProducer,Depends(produce_message)]):
    product_proto = product_pb2.Product(product_id= str(product_id), option = product_pb2.SelectOption.DELETE)
    serialized_product = product_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_product)
    product_proto = await consume_message_response()
    logger.info(f"Complete Product Proto: {product_proto}")
    if product_proto.message:
        return {"Product Deleted " : product_proto.message }
    elif product_proto.error_message or product_proto.http_status_code :
        raise HTTPException(status_code=product_proto.http_status_code, detail=product_proto.error_message)
    else:
        return{"Product not deleted ": product_proto.error_message }




