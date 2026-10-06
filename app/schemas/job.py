from datetime import date

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class JobBase(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    company: str = Field(min_length=1, max_length=120)
    company_url: AnyHttpUrl | None = None
    location: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=10_000)

    @field_validator("title", "company", "location", "description", mode="before")
    @classmethod
    def strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    """Partial update: only fields that are sent are changed."""

    title: str | None = Field(default=None, min_length=2, max_length=120)
    company: str | None = Field(default=None, min_length=1, max_length=120)
    company_url: AnyHttpUrl | None = None
    location: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=10, max_length=10_000)
    is_active: bool | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    company_url: str | None
    location: str
    description: str
    date_posted: date
    is_active: bool
    owner_id: int


class JobPage(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    size: int
    pages: int
