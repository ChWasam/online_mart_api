from fastapi import FastAPI,Depends,HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
from aiokafka import AIOKafkaProducer , AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from app.router import user
from app import payment_pb2
from app import settings
from app import db ,kafka, model, auth
from app.consumer import main
import uuid 
from uuid import UUID 
import asyncio
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


#  Function to consume all messages other than list of all orders from kafkatopic
async def consume_message_response_get():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_GET}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_PAYMENT_GET}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = payment_pb2.Payment()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()







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
    task2 = loop.create_task(main.consume_message_from_create_order())
    try:
        yield
    finally:
        for task in [task1,task2]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# verify_token:Annotated[model.User,Depends(auth.verify_access_token)]

app:FastAPI = FastAPI(lifespan=lifespan )

app.include_router(router=user.user_router)


# Home Endpoint
@app.get("/")
async def read_root():
    return {"Hello":"Payment Service"}


#  Endpoint to add payment 
@app.put("/payment", response_model=dict)
async def payment_request ( payment_request_detail:model.PaymentRequest , producer:Annotated[AIOKafkaProducer,Depends(produce_message)], verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):
    user_proto = payment_pb2.User(username = verify_token,
    service = payment_pb2.SelectService.PAYMENT,
    option = payment_pb2.SelectOption.CURRENT_USER)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user)

    user_proto = await kafka.consume_message_from_user_service()

    payment_proto = payment_pb2.Payment(
        user_id = user_proto.user_id,
        username = user_proto.username,
        email = user_proto.email,
        amount =payment_request_detail.amount,
        card_number = payment_request_detail.card_number,
        exp_month = payment_request_detail.exp_month,
        exp_year = payment_request_detail.exp_year,
        cvc  = payment_request_detail.cvc,
        order_id = str(payment_request_detail.order_id),
        )
    serialized_payment = payment_proto.SerializeToString()
    await producer.send_and_wait(f"{settings.KAFKA_TOPIC}",serialized_payment)
    payment_proto = await consume_message_response_get()

    if payment_proto.error_message :
        return {
            "Message": payment_proto.error_message
        }
    elif payment_proto.payment_status == payment_pb2.PaymentStatus.PAID:
        return {
            "payment_status" : "Paid ",
            "message" : "Payment Successful"
        }
    else:
        return {
            "payment_status" : "Pending",
            "message" : "Payment Unsuccessful"
        }




