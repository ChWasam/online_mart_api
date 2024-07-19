from sqlmodel import SQLModel,Field,create_engine,select, Session # type: ignore
from google.protobuf.json_format import MessageToDict # type: ignore
from fastapi import FastAPI,Depends,HTTPException # type: ignore
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # type: ignore
from contextlib import asynccontextmanager
from typing import Annotated
from aiokafka import AIOKafkaProducer , AIOKafkaConsumer # type: ignore
from aiokafka.admin import AIOKafkaAdminClient,NewTopic # type: ignore
from jose import jwt, JWTError # type: ignore
import asyncio
from app import db, kafka, model,settings,user_pb2,auth
from datetime import datetime, timezone, timedelta
from app.consumer import main
from uuid import UUID 
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



#  It contains all the instructions that will run when the application will start
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_table()
    await kafka.create_topic()
    loop = asyncio.get_event_loop()
    task = loop.create_task(main.consume_message_request())
    # task2 = loop.create_task(main.consume_message_request_from_order_service())
    try:
        yield
    finally:
        # for task in [task1,task2]:
            task.cancel()
            await task



# Home Endpoint
app:FastAPI = FastAPI(lifespan=lifespan )


@app.get("/")
async def read_root():
    return {"Hello":"User Service"}


#  Register user  user/register 
@app.post("/user/register")
async def register_user(register:Annotated[model.RegisterUser,Depends(model.RegisterUser)]):
    user_proto = user_pb2.User(username = register.username, email = register.email , password = register.password, option = user_pb2.SelectOption.REGISTER)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC, serialized_user)
    
    user_proto = await kafka.consume_message_response()
    if user_proto.error_message or user_proto.http_status_code :
        raise HTTPException(status_code=user_proto.http_status_code, detail=user_proto.error_message)
    else:
        user_return_from_db = {
                    "id":user_proto.id,
                    "user_id":str(user_proto.user_id),
                    "username":user_proto.username,
                    "email":user_proto.email,
                    "password":user_proto.password,
        }
        return user_return_from_db















