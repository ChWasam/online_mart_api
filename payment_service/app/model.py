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


class Payment(SQLModel, table = True):
    id : int|None = Field(default = None , primary_key= True)
    payment_id:UUID = Field(default_factory=uuid.uuid4, index=True)
    order_id:UUID = Field(index=True)
    user_id:UUID = Field(index=True)
    payment_status:str = Field(default="Pending", index=True)

class PaymentRequest (SQLModel):
    amount: float
    card_number: int
    exp_month: int
    exp_year: int
    cvc: int
    order_id: str


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


