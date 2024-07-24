from app import settings
from aiokafka import AIOKafkaConsumer # type: ignore
from app import notification_pb2, kafka, handle_email
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consume_message_from_user_registration():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_TO_CONSUME_NEW_USER}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER}",
    auto_offset_reset='earliest'
    )
    await kafka.retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = notification_pb2.User()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                if new_msg.option == notification_pb2.SelectOption.REGISTER:
                    body = f"""Hi {new_msg.username},
Welcome to Online Mart! You have successfully signed in. Explore our wide range of products and enjoy seamless shopping!"""
                    subject = f"""New User Registration """
                    await handle_email.send_email(body = body , subject = subject, user_email = new_msg.email)
                    # await handle_register_user(new_msg)
                    pass
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()