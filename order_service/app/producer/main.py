from sqlmodel import SQLModel,Field,create_engine,select, Session
from google.protobuf.json_format import MessageToDict
from fastapi import FastAPI,Depends,HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
from aiokafka import AIOKafkaProducer , AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from app.router import user
from app import order_pb2
from app import settings
from app import db ,kafka, model, auth
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
        NewTopic(name=f"{settings.KAFKA_TOPIC}", num_partitions=2, replication_factor=1),
        NewTopic(name=f"{settings.KAFKA_TOPIC_GET}", num_partitions=2, replication_factor=1),
    ]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only= False)
    except Exception as e:
        logger.error ( "Error creating topics:: {e}")
    finally:
        await admin_client.close()

#  Function to consume list of all orders from kafkatopic
async def consume_message_response_get_all():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer : {msg}")
            try:
                new_msg = order_pb2.OrderList()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()

#  Function to consume all messages other than list of all orders from kafkatopic
async def consume_message_response_get():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = order_pb2.Order()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()




# Pydantic dataValidation 
class Orders(SQLModel):
    id : int|None = Field(default = None , primary_key= True)
    order_id:UUID = Field(default_factory=uuid.uuid4, index=True)
    product_id:UUID = Field(index=True)
    user_id:UUID = Field(index=True)
    quantity:int = Field(index=True)
    shipping_address:str = Field(index=True)
    customer_notes:str = Field(index=True)

class OrdersInputField(SQLModel):
    quantity:int = Field(index=True)
    shipping_address:str = Field(index=True)
    customer_notes:str = Field(index=True)



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
    task2 = loop.create_task(main.consume_message_from_payment_service())
    try:
        yield
    finally:
        for task in [task1, task2]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

#  we get error  (We solve it by 
#             except asyncio.CancelledError:
                # pass
# )

# order  | WARNING:  WatchFiles detected changes in 'app/producer/main.py'. Reloading...
# order  | INFO:     Shutting down
# order  | INFO:     Waiting for application shutdown.
# order  | INFO:aiokafka.consumer.group_coordinator:LeaveGroup request succeeded
# order  | ERROR:    Traceback (most recent call last):
# order  |   File "/usr/local/lib/python3.12/site-packages/starlette/routing.py", line 732, in lifespan
# order  |     async with self.lifespan_context(app) as maybe_state:
# order  |   File "/usr/local/lib/python3.12/contextlib.py", line 217, in __aexit__
# order  |     await anext(self.gen)
# order  |   File "/code/app/producer/main.py", line 142, in lifespan
# order  |     try:
# order  |   File "/code/app/consumer/main.py", line 301, in consume_message_request
# order  |     async for msg in consumer:
# order  |   File "/usr/local/lib/python3.12/site-packages/aiokafka/consumer/consumer.py", line 1268, in __anext__
# order  |     return (await self.getone())
# order  |             ^^^^^^^^^^^^^^^^^^^
# order  |   File "/usr/local/lib/python3.12/site-packages/aiokafka/consumer/consumer.py", line 1154, in getone
# order  |     msg = await self._fetcher.next_record(partitions)
# order  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# order  |   File "/usr/local/lib/python3.12/site-packages/aiokafka/consumer/fetcher.py", line 1041, in next_record
# order  |     await waiter
# order  | asyncio.exceptions.CancelledError


# verify_token:Annotated[model.User,Depends(auth.verify_access_token)]

app:FastAPI = FastAPI(lifespan=lifespan )

app.include_router(router=user.user_router)


# Home Endpoint
@app.get("/")
async def read_root():
    return {"Hello":"Order Service"}

# Endpoint to get all the orders
@app.get("/orders", response_model= list[Orders])
async def get_all_orders(producer:Annotated[AIOKafkaProducer,Depends(produce_message)], verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):
    order_proto = order_pb2.Order(user_id = str(verify_token.user_id), option = order_pb2.SelectOption.GET_ALL)
    serialized_order = order_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_order)
    
    order_list_proto = await consume_message_response_get_all()

    order_list = [
        {
                "id":order.id,
                "user_id": str(order.user_id),
                "order_id":str(order.order_id) ,
                "product_id":str(order.product_id),
                "quantity":order.quantity,
                'shipping_address':order.shipping_address,
                "customer_notes":order.customer_notes,
        }
        for order in order_list_proto.orders
    ]
    return order_list


#  Endpoint to get the single order based on endpoint 
@app.get("/order/{order_id}", response_model=dict)
async def get_a_order(order_id:UUID, producer:Annotated[AIOKafkaProducer,Depends(produce_message)], verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):
    order_proto = order_pb2.Order(order_id =str(order_id), user_id = str(verify_token.user_id) ,  option = order_pb2.SelectOption.GET)
    serialized_order = order_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_order)

    order_proto = await consume_message_response_get()

    if order_proto.error_message or order_proto.http_status_code :
        raise HTTPException(status_code=order_proto.http_status_code, detail=order_proto.error_message)
    else:
        return {
                "id":order_proto.id,
                "user_id": str(order_proto.user_id),
                "order_id":str(order_proto.order_id) ,
                "product_id":str(order_proto.product_id),
                "quantity":order_proto.quantity,
                'shipping_address':order_proto.shipping_address,
                "customer_notes":order_proto.customer_notes,
        }


#  Endpoint to add order to database 
@app.post("/order/{product_id}", response_model=dict)
async  def add_order(product_id:UUID, order:OrdersInputField , producer:Annotated[AIOKafkaProducer,Depends(produce_message)], verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):
    logger.info(f"Username that we get after decoding token and ready to send to user_service to get user detail:{verify_token}")
    user_proto = order_pb2.User(username = verify_token,
    service = order_pb2.SelectService.ORDER,
    option = order_pb2.SelectOption.CURRENT_USER)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user)

    user_proto = await kafka.consume_message_from_user_service()

    order_proto = order_pb2.Order(
        product_id = str(product_id), 
        user_id = str(user_proto.user_id),
        username = user_proto.username,
        email = user_proto.email,
        quantity = order.quantity,
        shipping_address = order.shipping_address ,
        customer_notes = order.customer_notes,
        order_status = order_pb2.OrderStatus.IN_PROGRESS,
        payment_status =order_pb2.PaymentStatus.PENDING,
        option = order_pb2.SelectOption.CREATE)

    serialized_order = order_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_order)

    order_proto = await consume_message_response_get()

    if order_proto.quantity is None:
        order_proto.quantity = 0
    if order_proto.error_message and order_proto.http_status_code:
        raise HTTPException(status_code=order_proto.http_status_code, detail=order_proto.error_message)
    else:
        return{"Order Created":{                    
                    "id":order_proto.id,
                    "user_id": str(order_proto.user_id),
                    "order_id" : str(order_proto.order_id),
                    "product_id":str(order_proto.product_id),
                    "quantity":order_proto.quantity,
                    "shipping_address":order_proto.shipping_address,
                    "customer_notes":order_proto.customer_notes
                    }}


#  Endpoint to update order to database 
@app.put("/order/{order_id}", response_model = dict)
async  def update_order (order_id:UUID, order:OrdersInputField , producer:Annotated[AIOKafkaProducer,Depends(produce_message)], verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):

    order_proto = order_pb2.Order(order_id= str(order_id),user_id= str(verify_token.user_id), quantity = order.quantity, shipping_address = order.shipping_address , customer_notes = order.customer_notes, option = order_pb2.SelectOption.UPDATE)
    serialized_order = order_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_order)

    order_proto = await consume_message_response_get()

    if order_proto.quantity is None:
        order_proto.quantity = 0

    if order_proto.error_message and order_proto.http_status_code:
        raise HTTPException(status_code=order_proto.http_status_code, detail=order_proto.error_message)
    elif order_proto.error_message :
        return {"Order not created": f"{order_proto.error_message}"}
    else:
        return{"Order Updated": {                    
                    "id":order_proto.id,
                    "user_id" : str(order_proto.user_id),
                    "order_id" : str(order_proto.order_id),
                    "product_id":str(order_proto.product_id),
                    "quantity":order_proto.quantity,
                    "shipping_address":order_proto.shipping_address,
                    "customer_notes":order_proto.customer_notes
                }}


#  Endpoint to delete order from database 
@app.delete("/order/{order_id}", response_model=dict)
async  def delete_order (order_id:UUID, producer:Annotated[AIOKafkaProducer,Depends(produce_message)], verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):
    order_proto = order_pb2.Order(order_id= str(order_id),user_id= str(verify_token.user_id),  option = order_pb2.SelectOption.DELETE)
    serialized_order = order_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_order)

    order_proto = await consume_message_response_get()
    
    if order_proto.message:
        return {"Order Deleted " : order_proto.message }
    elif order_proto.error_message or order_proto.http_status_code :
        raise HTTPException(status_code=order_proto.http_status_code, detail=order_proto.error_message)
    else:
        return{"Order not deleted ": order_proto.error_message }



