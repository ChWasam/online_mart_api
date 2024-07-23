from passlib.context import CryptContext # type: ignore
from app import kafka ,db,settings, payment_pb2
from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from sqlmodel import SQLModel, Session, select
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError # type: ignore


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


async def verify_access_token(token:Annotated[str,Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(status_code=401, 
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}   
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str| None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        return None
    user_proto = order_pb2.User(username = username, option = order_pb2.SelectOption.CURRENT_USER)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user)

    user_proto = await kafka.consume_message_from_user_service()

    if user_proto.error_message or user_proto.http_status_code:
        raise credentials_exception
    
    return user_proto




# verify refresh token
def verify_refresh_token(token:str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
    





