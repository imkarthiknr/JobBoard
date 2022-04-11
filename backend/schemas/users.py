from re import S
from turtle import st
from typing import Optional 
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
     username: str
     email: EmailStr
     password: str
     