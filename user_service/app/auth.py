from passlib.context import CryptContext # type: ignore
from app import kafka ,db,settings
from app.model import User
from sqlmodel import SQLModel, Session, select
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError # type: ignore




#  Password Hashing 
# poetry add "passlib[bycrypt]" 

pwd_context = CryptContext(schemes="bcrypt")

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(password, hash_password):
    return pwd_context.verify(password, hash_password)


#  Check user in database 

def check_user_in_db(username, email):
    with Session(db.engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            user = session.exec(select(User).where(User.email == email)).first()
            if user:
                return user
        return user

#  Genereate access_token
def generate_token(data: dict, expires_delta: timedelta|None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

    

