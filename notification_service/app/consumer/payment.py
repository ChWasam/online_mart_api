from app import settings
from aiokafka import AIOKafkaConsumer # type: ignore
from app import notification_pb2, kafka, handle_email
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consume_message_from_payment_done():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_TO_CONSUME_PAYMENT_DONE}",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_PAYMENT_DONE}",
    auto_offset_reset='earliest'
    )
    await kafka.retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = notification_pb2.Payment()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")


                if new_msg.payment_status == notification_pb2.PaymentStatus.PAID:
                    body = f"""Hi {new_msg.username},
Thank you for your purchase! Your payment has been successfully processed. Your order has been dispatched and is on its way! """
                    subject = f"""Payment Confirmation and Order Dispatch Notification from Online Mart"""
                    await handle_email.send_email(body = body , subject = subject, user_email = new_msg.email)
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()