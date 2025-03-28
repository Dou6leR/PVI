from pydantic import field_validator, BaseModel, Field
import datetime
import re


class StudentCreate(BaseModel):
    group: str = Field(..., min_length=1, max_length=20)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    gender: str = Field(..., pattern="^(Male|Female|Other)$")
    birthday: datetime.date = Field(...)

    @field_validator("first_name", "last_name")
    def validate_name(cls, value):
        if not re.match(r"^[A-Za-zА-Яа-я]{2,}$", value):
            raise ValueError("Must be at least 2 characters and contain only letters")
        return value

    @field_validator("birthday")
    def validate_birthday(cls, value):
        today = datetime.date.today()
        birthday = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if not (16 <= birthday <= 100):
            raise ValueError("birthday must be between 16 and 100 years")
        return value


class StudentUpdate(BaseModel):
    group: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    birthday: datetime.date | None = None
    status: bool | None = None

    @field_validator("first_name", "last_name")
    def validate_name(cls, value):
        if not re.match(r"^[A-Za-zА-Яа-я]{2,}$", value):
            raise ValueError("Must be at least 2 characters and contain only letters")
        return value

    @field_validator("birthday")
    def validate_birthday(cls, value):
        today = datetime.date.today()
        birthday = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if not (16 <= birthday <= 100):
            raise ValueError("birthday must be between 16 and 100 years")
        return value

    @field_validator("gender")
    def validate_gender(cls, value):
        if not re.match(r"^Male|Female|Other$", value):
            raise ValueError("Gender must be Male/Female or Other")
        return value


class StudentResponse(BaseModel):
    id: int
    group: str
    first_name: str
    last_name: str
    gender: str
    birthday: datetime.date
    status: bool


class StudentsResponse(BaseModel):
    data: list[StudentResponse]
    