from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends,HTTPException
from typing import Annotated
from app import order_pb2,kafka,settings, auth, model
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



user_router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}}
)


# Login Endpoint

@user_router.post("/login")
async def login_user(login:Annotated[OAuth2PasswordRequestForm,Depends(OAuth2PasswordRequestForm)]):
    user_proto = order_pb2.User(username = login.username, password = login.password, option = order_pb2.SelectOption.LOGIN)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user)

    user_proto = await kafka.consume_message_from_user_service()

    logger.info(f"getting user_proto:{user_proto}")
    if user_proto.error_message or user_proto.http_status_code :
        raise HTTPException(status_code=user_proto.http_status_code, detail=user_proto.error_message)
    return {"access_token":user_proto.access_token, "token_type":"bearer", "refresh_token":user_proto.refresh_token}



# user/me

@user_router.get("/me")
async def get_current_user(verify_token:Annotated[model.User,Depends(auth.verify_access_token)]):
    return {
            "id" : verify_token.id,
            "user_id" : str(verify_token.user_id),
            "username" : verify_token.username,
            "email" : verify_token.email,
            "password" : verify_token.password,
    }


# refresh tokens endpoint

@user_router.post("/refresh_token")
async def refresh_token(old_refresh_token:str):
    credentials_exception = HTTPException(status_code=401, 
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"} 
    )
    email = auth.verify_refresh_token(old_refresh_token)
    if not email:
        raise credentials_exception
    user_proto = order_pb2.User(email = email, option = order_pb2.SelectOption.REFRESH_TOKEN)
    serialized_user = user_proto.SerializeToString()
    await kafka.produce_message(settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user)

    user_proto = await kafka.consume_message_from_user_service()

    if user_proto.error_message or user_proto.http_status_code :
        raise credentials_exception
    return {"access_token":user_proto.access_token, "token_type":"bearer", "refresh_token":user_proto.refresh_token}