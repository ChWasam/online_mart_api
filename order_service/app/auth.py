from passlib.context import CryptContext # type: ignore
from app import kafka ,db,settings, order_pb2
from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from sqlmodel import SQLModel, Session, select
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError # type: ignore
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def verify_access_token(token:Annotated[str,Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(status_code=401, 
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}   
    )
    logger.info(f"Value of token that we receive at verify_access_token :{token}")
    try:
        logger.info(f"Value of token in the try block  :{token}")

        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)

        logger.info(f"Value of payload in the try block  :{payload}")
        logger.info(f"Value of token under payload  :{token}")
        username: str| None = payload.get("sub")
        logger.info(f"Username that we get after decoding token:{username}")
        if username is None:
            raise credentials_exception
        
    except JWTError:
        return credentials_exception

    return username




# verify refresh token
def verify_refresh_token(token:str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
        return payload.get("sub")
    except JWTError:
        return None
    





