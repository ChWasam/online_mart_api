from pydantic import BaseModel 
from fastapi import Form 
from typing import Annotated
from sqlmodel import SQLModel, Field
from pydantic import BaseModel 
from fastapi import Form 
from typing import Annotated
from sqlmodel import SQLModel, Field
import uuid
from uuid import UUID


class User (SQLModel):
    id : int| None = Field(default=None, primary_key = True)
    user_id: UUID = Field(default_factory=uuid.uuid4, index=True)
    username: str = Field(index = True)
    email: str = Field(index = True)
    password: str = Field(index = True)

class RegisterUser (BaseModel):
            username: Annotated[
            str,
            Form(),
        ]
            email: Annotated[
            str,
            Form(),
        ]
            password: Annotated[
            str,
            Form(),
        ]


