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


