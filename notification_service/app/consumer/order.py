from app import settings
from aiokafka import AIOKafkaConsumer # type: ignore
from app import notification_pb2, kafka, handle_email
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consume_message_from_create_order():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_TO_CONSUME_ORDER_CREATED}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_ORDER_CREATED}",
    auto_offset_reset='earliest'
    )
    await kafka.retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = notification_pb2.Order()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                if new_msg.option == notification_pb2.SelectOption.CREATE:
                    body = f"""Hi {new_msg.username},
Thankyou for your order. Your order has been placed successfully.To Proceed, please make the payment. we will notify you once the payment is done."""
                    subject = f"""Order Confirmation"""
                    await handle_email.send_email(body = body , subject = subject, user_email = new_msg.email)
                    # await handle_register_user(new_msg)
                    pass
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()