# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Pydantic response schemas for notification endpoints.
# First Written on: Tuesday, 19-May-2026
# Edited on: Wednesday, 15-Jul-2026

from pydantic import BaseModel


class TestPushResponseSchema(BaseModel):
    sent: bool
    detail: str
