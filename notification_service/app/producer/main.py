from fastapi import FastAPI # type: ignore
from contextlib import asynccontextmanager
import asyncio
from app.consumer import order,user,payment
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



#  It contains all the instructions that will run when the application will start
@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(user.consume_message_from_user_registration())
    task2 = loop.create_task(order.consume_message_from_create_order())
    task3 = loop.create_task(payment.consume_message_from_payment_done())
    try:
        yield
    finally:
        for task in [task1,task2,task3]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass



# Home Endpoint
app:FastAPI = FastAPI(lifespan=lifespan )


@app.get("/")
async def read_root():
    return {"Hello":"Notification Service"}

















