from passlib.context import CryptContext # type: ignore
from app import kafka ,db,settings
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from sqlmodel import SQLModel, Session, select
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError # type: ignore


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def verify_access_token(token:Annotated[str,Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# verify refresh token
def verify_refresh_token(token:str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None