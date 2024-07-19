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



# user login 
@app.post("/user/login")
async def login_user(login:Annotated[OAuth2PasswordRequestForm,Depends(OAuth2PasswordRequestForm)]):
    user_proto = user_pb2.User(username = login.username, password = login.password, option = user_pb2.SelectOption.LOGIN)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC, serialized_user)

    user_proto = await kafka.consume_message_response()

    if user_proto.error_message or user_proto.http_status_code :
        raise HTTPException(status_code=user_proto.http_status_code, detail=user_proto.error_message)
    return {"access_token":user_proto.access_token, "token_type":"bearer", "refresh_token":user_proto.refresh_token}



#  user/me
@app.get("/user/me")
async def get_current_user(verify_token:Annotated[str,Depends(auth.verify_access_token)]):
    credentials_exception = HTTPException(status_code=401, 
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}   
    )
    if not verify_token:
        raise credentials_exception
    user_proto = user_pb2.User(username = verify_token, option = user_pb2.SelectOption.CURRENT_USER)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC, serialized_user)

    user_proto = await kafka.consume_message_response()

    if user_proto.error_message or user_proto.http_status_code:
        raise credentials_exception
    return user_proto.username


@app.post("/user/refresh_token")
async def refresh_token(old_refresh_token:str):
    credentials_exception = HTTPException(status_code=401, 
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"} 
    )
    email = auth.verify_refresh_token(old_refresh_token)
    if not email:
        raise credentials_exception
    user_proto = user_pb2.User(email = email, option = user_pb2.SelectOption.REFRESH_TOKEN)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC, serialized_user)
    user_proto = await kafka.consume_message_response()
    if user_proto.error_message or user_proto.http_status_code :
        raise credentials_exception
    return {"access_token":user_proto.access_token, "token_type":"bearer", "refresh_token":user_proto.refresh_token}




