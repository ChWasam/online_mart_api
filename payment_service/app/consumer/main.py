from sqlmodel import SQLModel, Field, create_engine, select, Session
from app import settings, payment_pb2,db, model
from app.stripe import payment
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
import logging
import uuid
from uuid import UUID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




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


#  Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs 
async def consume_message_request():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_PAYMENT,
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = payment_pb2.Payment()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message: {new_msg}")
            if new_msg.amount is None:
                new_msg.amount = 0

            logger.info(f"new_msg.amount: {new_msg.amount}")
            payment_request = model.PaymentRequest(
                amount =new_msg.amount,
                card_number = new_msg.card_number,
                exp_month = new_msg.exp_month,
                exp_year = new_msg.exp_year,
                cvc  = new_msg.cvc,
                order_id = str(new_msg.order_id),
            )
            with Session(db.engine) as session:
                select_order = session.exec(select(model.Payment).where(model.Payment.order_id == uuid.UUID(new_msg.order_id))).first()
                if select_order:
                    payment_response = await payment.create_payment(payment_request)
                    if select_order.payment_status == "Payment Done":
                        payment_proto = payment_pb2.Payment(
                                error_message=f"Payment Already Done",
                            )
                        serialized_payment = payment_proto.SerializeToString()
                        await produce_message(settings.KAFKA_TOPIC_GET, serialized_payment)
                    else:    
                        if payment_response == payment_pb2.PaymentStatus.PAID:
                            select_order.payment_status = "Payment Done"
                            session.add(select_order)
                            session.commit()
                            payment_proto = payment_pb2.Payment(
                                user_id = str(new_msg.user_id),
                                order_id = str(select_order.order_id),
                                username = new_msg.username,
                                email = new_msg.email,
                                payment_status = payment_pb2.PaymentStatus.PAID
                            )
                            serialized_payment = payment_proto.SerializeToString()
                            await produce_message(settings.KAFKA_TOPIC_GET, serialized_payment)
                        else:
                            select_order.payment_status = "Payment Failed"
                            session.add(select_order)
                            session.commit()

                            payment_proto = payment_pb2.Payment(
                                order_id = str(payment.order_id),
                                payment_status = payment_pb2.PaymentStatus.FAILED
                            )
                            serialized_payment = payment_proto.SerializeToString()
                            await produce_message(settings.KAFKA_TOPIC_GET, serialized_payment)
                else:
                    payment_proto = payment_pb2.Payment(
                        error_message = "You haven't placed any order yet"

                    )
                    serialized_payment = payment_proto.SerializeToString()
                    await produce_message(settings.KAFKA_TOPIC_GET, serialized_payment)
                    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()



#  Function to consume message from the create product API on the producer side of product service  and update product with id in inventory service 
async def consume_message_from_create_order():
    consumer = AIOKafkaConsumer(
        f"{(settings.KAFKA_TOPIC_GET_FROM_ORDER).strip()}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{(settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER)}",
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"Received message: {msg}")
            new_msg = payment_pb2.Order()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received msg.value: {new_msg}")
            if new_msg.option == payment_pb2.SelectOption.CREATE:
                payment = model.Payment(
                    order_id = uuid.UUID(new_msg.order_id),
                    user_id = uuid.UUID(new_msg.user_id)
                )
                with Session(db.engine) as session:
                    session.add(payment)
                    session.commit()
            elif new_msg.option == payment_pb2.SelectOption.DELETE:
                with Session(db.engine) as session:
                    payment = session.exec(select(model.Payment).where(model.Payment.order_id == new_msg.order_id)).first()
                    if payment:
                        session.delete(payment)
                        session.commit()               
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()
