from sqlmodel import SQLModel, Field
from pydantic import field_validator
import datetime
import re

class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    group: str = Field(..., min_length=1, max_length=20)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    gender: str = Field(..., regex="^(Male|Female|Other)$")
    birthday: datetime.date = Field(...)
    status: bool = Field(...)
    password: str = Field(..., min_length=6)

    @field_validator("first_name", "last_name")
    def validate_name(cls, value):
        if not re.match(r"^[A-Za-zА-Яа-я]{2,}$", value):
            raise ValueError("Must be at least 2 characters and contain only letters")
        return value

    @field_validator("birthday")
    def validate_birthday(cls, value):
        today = datetime.date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if not (16 <= age <= 100):
            raise ValueError("Age must be between 16 and 100 years")
        return value

