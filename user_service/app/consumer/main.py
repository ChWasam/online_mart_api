from sqlmodel import SQLModel, Field, create_engine, select, Session
from app import settings, user_pb2,db, kafka,auth
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from datetime import datetime, timezone, timedelta
import asyncio
import logging
import uuid
from uuid import UUID

from app import auth, model

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


                
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
                http_status_code=400
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)

async def handle_register_user(new_msg):
    user = auth.check_user_in_db(new_msg.username, new_msg.email)
    if user:
        user_proto = user_pb2.User(
        error_message=f"User with these credentials already exists in database",
        http_status_code=409
        )
        serialized_user = user_proto.SerializeToString()
        await kafka.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
    else:
        user = model.User(
            username=new_msg.username,
            email=new_msg.email,
            password=auth.hash_password(new_msg.password),
        )
        with Session(db.engine) as session:
            session.add(user)
            session.commit()
            logger.info(f"User added to database: {user}")
            session.refresh(user)
            if user:
                user_proto = user_pb2.User(
                    id=user.id,
                    user_id=str(user.user_id),
                    username=user.username,
                    email=user.email,
                    password= user.password,
                    option = user_pb2.SelectOption.REGISTER,
                )
                serialized_user = user_proto.SerializeToString()
                await kafka.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
                logger.info(f"User added to database and sent back: {user_proto}")
            else:
                user_proto = user_pb2.User(
                    error_message=f"{new_msg.username} is unable to add in database",
                    http_status_code=404
                )
                serialized_user = user_proto.SerializeToString()
                await kafka.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)


async def handle_login(new_msg):
    user = auth.check_user_in_db(new_msg.username, new_msg.password)
    if user:
        if auth.verify_password(new_msg.password, user.password):
        # Here i wish to generate a token and return it to the user
            expire_time = timedelta(minutes = settings.JWT_EXPIRY_TIME)
            access_token = auth.generate_token(data = {"sub":user.username}, expires_delta = expire_time)
        # Refresh token
            expire_time_for_refresh_token = timedelta(days = 15)
            refresh_token = auth.generate_token(data = {"sub":user.email}, expires_delta = expire_time_for_refresh_token)

            user_proto = user_pb2.User(
                access_token = access_token,
                refresh_token = refresh_token,
                option = user_pb2.SelectOption.LOGIN
            )
            serialized_user = user_proto.SerializeToString()
            if new_msg.service == user_pb2.SelectService.PAYMENT:
                await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
            elif new_msg.service == user_pb2.SelectService.ORDER:
                await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)

            logger.info(f"User logged in and sent back: {user_proto}")
        else:
            user_proto = user_pb2.User(
                error_message=f"Password is incorrect",
                http_status_code=401
            )
            serialized_user = user_proto.SerializeToString()

            if new_msg.service == user_pb2.SelectService.PAYMENT:
                await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
            elif new_msg.service == user_pb2.SelectService.ORDER:
                await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)
    else:
        user_proto = user_pb2.User(
        error_message=f"{new_msg.username} is not registered in database", 
        http_status_code=404
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)
            


#  Function to handle update product request from producer side from where API is called to update product to database 
async def handle_verify_user(new_msg):
    logger.info(f"Username we get at consumer on user service to verify it: {new_msg.username}")
    user = auth.check_user_in_db(new_msg.username, new_msg.email)
    logger.info(f"detail of user after checking it from database: {user}")
    if not user:
        user_proto = user_pb2.User(
        error_message=f"User with these credentials do not exists in database",
        http_status_code=404
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)
    else:
        user_proto = user_pb2.User(
            id=user.id,
            user_id=str(user.user_id),
            username=user.username,
            email=user.email,
            password= user.password,
            option = user_pb2.SelectOption.CURRENT_USER,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)
        logger.info(f"User verified and username sent back: {user_proto}")

async def handle_refresh_token(new_msg):
    user = auth.check_user_in_db(new_msg.username, new_msg.email)
    if not user:
        user_proto = user_pb2.User(
        error_message=f"User with these credentials do not exists in database",
        http_status_code=404
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)
    else:
    # Here i wish to generate a token and return it to the user
        expire_time = timedelta(minutes = settings.JWT_EXPIRY_TIME)
        access_token = auth.generate_token(data = {"sub":user.username}, expires_delta = expire_time)
    # Refresh token
        expire_time_for_refresh_token = timedelta(days = 15)
        refresh_token = auth.generate_token(data = {"sub":user.email}, expires_delta = expire_time_for_refresh_token)

        user_proto = user_pb2.User(
            access_token = access_token,
            refresh_token = refresh_token,
            option = user_pb2.SelectOption.REFRESH_TOKEN
            )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user)
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.produce_message(settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user)
        logger.info(f"User verified and email sent back: {user_proto}")


#  Function to handle delete product request from producer side from where API is called to delete product from database 
async def handle_delete_product(product_id):
    with Session(db.engine) as session:
        product = session.exec(select(Product).where(Product.product_id == product_id)).first()
        if product:
            session.delete(product)
            session.commit()
            product_proto = product_pb2.Product(
                product_id = product_id,
                message=f"Product with product_id: {product_id} deleted!",
                option = product_pb2.SelectOption.DELETE
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)
            logger.info(f"Product deleted and confirmation sent back: {product_proto}")
        else:
            product_proto = product_pb2.Product(
                error_message=f"No Product with product_id: {product_id} found!",
                http_status_code=404
            )
            serialized_product = product_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)


#  Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs 
async def consume_message_request():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_USER,
        auto_offset_reset='earliest'
    )
    await kafka.retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = user_pb2.User()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message: {new_msg}")

            if new_msg.option == user_pb2.SelectOption.REGISTER:
                await handle_register_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.LOGIN:
                await handle_login(new_msg)
            elif new_msg.option == user_pb2.SelectOption.CURRENT_USER:
                await handle_verify_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.REFRESH_TOKEN:
                await handle_refresh_token(new_msg)
            # elif new_msg.option == user_pb2.SelectOption.DELETE:
            #     await handle_delete_product(new_msg.product_id)
            else:
                logger.warning(f"Unknown option received: {new_msg.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()






