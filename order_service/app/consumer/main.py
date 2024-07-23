from sqlmodel import SQLModel, Field, create_engine, select, Session
from app import settings, order_pb2,db
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
import logging
import uuid
from uuid import UUID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



#  Used for data validation and table fields 
class Orders(SQLModel, table=True):
    __tablename__ = "orders_table"
    id : int|None = Field(default = None , primary_key= True)
    order_id:UUID = Field(default_factory=uuid.uuid4, index=True)
    product_id:UUID = Field(index=True)
    user_id:UUID = Field(index=True)
    quantity:int = Field(index=True)
    shipping_address:str = Field(index=True)
    customer_notes:str = Field(index=True)
    order_status:str = Field(default="In_progress", index=True)
    payment_status:str = Field(default="Pending", index=True)

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

#  Function to handle get all orders request from producer side from where API is called to get all orders 
async def handle_get_all_orders(user_id):
    with Session(db.engine) as session:
        orders_list = session.exec(select(Orders).where(Orders.user_id == user_id)).all()
        orders_list_proto = order_pb2.OrderList()
        for order in orders_list:
            order_proto = order_pb2.Order(
                id=order.id,
                user_id = str(order.user_id),
                order_id=str(order.order_id) ,
                product_id=str(order.product_id),
                quantity=order.quantity,
                shipping_address=order.shipping_address,
                customer_notes=order.customer_notes,
            )
            orders_list_proto.orders.append(order_proto)
        serialized_order_list = orders_list_proto.SerializeToString()
        await produce_message(settings.KAFKA_TOPIC_GET, serialized_order_list )
        logger.info(f"List of orders sent back from database: {orders_list_proto}")


#  Function to handle get order request from producer side from where API is called to get an order 
async def handle_get_order(new_msg):
    with Session(db.engine) as session:
        user_orders = session.exec(select(Orders).where(Orders.user_id == uuid.UUID(new_msg.user_id))).all()
        order = next( (order for order in user_orders if order.order_id == uuid.UUID(new_msg.order_id)),None)
        if order:
            order_proto = order_pb2.Order(
                id=order.id,
                user_id = str(order.user_id),
                order_id=str(order.order_id) ,
                product_id=str(order.product_id),
                quantity=order.quantity,
                shipping_address=order.shipping_address,
                customer_notes=order.customer_notes,
            )
            serialized_order = order_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
            logger.info(f"Order sent back from database: {order_proto}")
        else:
            order_proto = order_pb2.Order(
                error_message=f"No Order with order_id: {new_msg.order_id} found!",
                http_status_code=400
            )
            serialized_order = order_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)


##################################### ADD ORDER #######################################
#  Function to consume message from inventory for inventory check 
async def consume_message_from_inventory_check():
    consumer = AIOKafkaConsumer(
    f"{settings.KAFKA_TOPIC_INVENTORY_CHECK_RESPONSE }",
    bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}",
    group_id= f"{settings.KAFKA_CONSUMER_GROUP_ID_FROM_INVENTORY_CHECK}",
    auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"Massage at the inventory check consumer on the order service side  : {msg}")
            try:
                new_msg = order_pb2.Order()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg at the inventory check consumer on the order service side :{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")    
    finally:
        await consumer.stop()


#  Function to handle inventory check 
async def handle_inventory_check(product_id,quantity,option):
            inventory_check_proto = order_pb2.Order(
            product_id=str(product_id),
            quantity = quantity,
            option = option
            )
            serialized_inventory_check = inventory_check_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_INVENTORY_CHECK_REQUEST, serialized_inventory_check)
            inventory_check = await consume_message_from_inventory_check()
            return inventory_check


#  Function to handle create order request from producer side from where API is called to add product to database 
async def handle_create_order(new_msg):
    if new_msg.quantity > 0:
        order = Orders(
            product_id=uuid.UUID(new_msg.product_id),
            user_id=uuid.UUID(new_msg.user_id),
            quantity=new_msg.quantity,
            shipping_address=new_msg.shipping_address,
            customer_notes=new_msg.customer_notes
        )
        inventory_check = await handle_inventory_check(order.product_id, order.quantity,order_pb2.SelectOption.CREATE)
        logger.info(f"Inventory check value  :{inventory_check}")
        if inventory_check.is_product_available:
            if inventory_check.is_stock_available:
                with Session(db.engine) as session:
                    session.add(order)
                    session.commit()
                    session.refresh(order)
                    if order:
                        logger.info(f"Order added to database: {order}")
                        order_proto = order_pb2.Order(
                        id=order.id,
                        order_id = str(order.order_id),
                        product_id=str(order.product_id),
                        user_id=str(order.user_id),
                        username= new_msg.username,
                        email= new_msg.email ,
                        quantity=order.quantity,
                        shipping_address=order.shipping_address,
                        customer_notes=order.customer_notes,
                        option = order_pb2.SelectOption.CREATE
                        )
                        serialized_order = order_proto.SerializeToString()
                        await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
                        logger.info(f"Order updated in database and sent back: {order_proto}")
                    else:
                        order_proto = order_pb2.Order(
                            error_message=f"No order having product_id: {new_msg.product_id} created!",
                            http_status_code=404
                        )
                        serialized_order = order_proto.SerializeToString()
                        await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
            else:
                order_proto = order_pb2.Order(
                    error_message=f"Requested Quantity of product is not available",
                    http_status_code=404
                )
                serialized_order = order_proto.SerializeToString()
                await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
        else:
            order_proto = order_pb2.Order(
                error_message=f"Product with product id : {order.product_id} is not available for sale",
                http_status_code=404
            )
            serialized_order = order_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
    else:
        order_proto = order_pb2.Order(
        error_message=f"In order to proceed with order you need to specify the no of items you need to buy",
        http_status_code=404
            )
        serialized_order = order_proto.SerializeToString()
        await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)

        



##################################### Update ORDER ################################

#  Function to handle update order request from producer side from where API is called to update order to database 
async def handle_update_order(new_msg):
    with Session(db.engine) as session:
        user_orders = session.exec(select(Orders).where(Orders.user_id == uuid.UUID(new_msg.user_id))).all()
        order = next( (order for order in user_orders if order.order_id == uuid.UUID(new_msg.order_id)),None)
        logger.info(f"order: {order}")
        if order:
            new_quantity =order.quantity - new_msg.quantity
            #  Logic

            # 3 snarios                                     stock_level reserved_stock 
            # new_msg.quantity is smaller  3 - 2 = 1 (positive)    +1       -1
            # new_msg.quantity is larger   3- 4 = -1 (negative)    -1       +1
            # new_msg.quantity is same     3-3 = 0                 0        0

            inventory_check = await handle_inventory_check(order.product_id, new_quantity, order_pb2.SelectOption.UPDATE)
            if inventory_check.is_stock_available:
                logger.info(f"What is the value of new_msg.quantity: {new_msg.quantity}")
                if new_msg.quantity >= 0:
                    order.quantity = new_msg.quantity
                if new_msg.shipping_address:
                    order.shipping_address = new_msg.shipping_address
                if new_msg.customer_notes:
                    order.customer_notes = new_msg.customer_notes 
                session.add(order)
                session.commit()
                session.refresh(order)
                if order:
                    logger.info(f"Order added to database: {order}")
                    order_proto = order_pb2.Order(
                    id=order.id,
                    user_id = str(order.user_id),
                    order_id = str(order.order_id),
                    product_id=str(order.product_id),
                    quantity=order.quantity,
                    shipping_address=order.shipping_address,
                    customer_notes=order.customer_notes,
                    )
                    serialized_order = order_proto.SerializeToString()
                    await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
                    logger.info(f"Order updated in database and sent back: {order_proto}")
                else:
                    order_proto = order_pb2.Order(
                        error_message=f"No order having product_id: {new_msg.product_id} updated! because of database issue",
                        http_status_code=404
                    )
                    serialized_order = order_proto.SerializeToString()
                    await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)
            else:
                order_proto = order_pb2.Order(
                    error_message=f"Requested Quantity of product is not available",
                )
                serialized_order = order_proto.SerializeToString()
                await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)   
        else:
            order_proto = order_pb2.Order(
                error_message=f"No order with order_id : {new_msg.order_id} is available for sale",
            )
            serialized_order = order_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_order)

                
##################################### Delete ORDER ################################


#  Function to handle delete product request from producer side from where API is called to delete product from database 
async def handle_delete_order(new_msg):
    with Session(db.engine) as session:
        user_orders = session.exec(select(Orders).where(Orders.user_id == uuid.UUID(new_msg.user_id))).all()
        order = next( (order for order in user_orders if order.order_id == uuid.UUID(new_msg.order_id)),None)
        if order:
            if order.payment_status == "Payment Done":
                order_proto = order_pb2.Order(
                message=f"Order with order_id: {new_msg.order_id} can not be deleted! as payment is done and it has been dispatched from the warehouse",
                )
                serialized_product = order_proto.SerializeToString()
                await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)

            else:
                await handle_inventory_check(order.product_id, order.quantity, order_pb2.SelectOption.DELETE)
                session.delete(order)
                session.commit()
                order_proto = order_pb2.Order(
                    message=f"Order with order_id: {new_msg.order_id} deleted!",
                )
                serialized_product = order_proto.SerializeToString()
                await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)
                logger.info(f"Order deleted and confirmation sent back: {order_proto}")
        else:
            order_proto = order_pb2.Order(
                error_message=f"No Order with order_id: {new_msg.order_id} found!",
                http_status_code=404
            )
            serialized_product = order_proto.SerializeToString()
            await produce_message(settings.KAFKA_TOPIC_GET, serialized_product)


#  Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs 
async def consume_message_request():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER,
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = order_pb2.Order()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message: {new_msg}")

            if new_msg.quantity is None:
                new_msg.quantity = 0

            logger.info(f"new_msg.quantity: {new_msg.quantity}")
            
            if new_msg.option == order_pb2.SelectOption.GET_ALL:
                await handle_get_all_orders(new_msg.user_id)
            elif new_msg.option == order_pb2.SelectOption.GET:
                await handle_get_order(new_msg)
            elif new_msg.option == order_pb2.SelectOption.CREATE:
                await handle_create_order(new_msg)
            elif new_msg.option == order_pb2.SelectOption.UPDATE:
                await handle_update_order(new_msg)
            elif new_msg.option == order_pb2.SelectOption.DELETE:
                await handle_delete_order(new_msg)
            else:
                logger.warning(f"Unknown option received: {new_msg.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()





#  Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs 
async def consume_message_from_payment_service():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_PAYMENT_DONE_FROM_PAYMENT,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_RESPONSE_FROM_PAYMENT,
        auto_offset_reset='earliest'
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = order_pb2.Payment()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message at order service from payment: {new_msg}")
            if new_msg.payment_status == order_pb2.PaymentStatus.PAID:
                with Session(db.engine) as session:
                    user_orders = session.exec(select(Orders).where(Orders.user_id == uuid.UUID(new_msg.user_id))).all()
                    order = next( (order for order in user_orders if order.order_id == uuid.UUID(new_msg.order_id)),None)
                    logger.info(f"order: {order}")
                    if order:
                        await handle_inventory_check(order.product_id, order.quantity, order_pb2.SelectOption.PAYMENT_DONE)
                        order.order_status = "Completed"
                        order.payment_status = "Payment Done"
                        session.add(order)
                        session.commit()
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()