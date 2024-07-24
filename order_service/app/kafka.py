from app import settings
from aiokafka import AIOKafkaProducer , AIOKafkaConsumer # type: ignore
from aiokafka.admin import AIOKafkaAdminClient,NewTopic # type: ignore
from app import order_pb2
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

#  Function to consume  messages from user service 
async def consume_message_from_user_service():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_RESPONSE_FROM_USER}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = order_pb2.User()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg we get from user_service :{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()

#  Function to produce message. 
async def produce_message(topic, message):
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await retry_async(producer.start)
    try:
        await producer.send_and_wait(topic, message)
    finally:
        await producer.stop()