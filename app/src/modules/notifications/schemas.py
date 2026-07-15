from pydantic import BaseModel


class TestPushResponseSchema(BaseModel):
    sent: bool
    detail: str
