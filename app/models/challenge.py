from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel

from app.auth.auth_utils import ObjectIdPydantic


class State(Enum):
    NOT_INIT = 1
    INIT = 2
    COMPLETE = 3


class ChallengeCreate(BaseModel):
    title: str
    description: str
    metric: str
    limit_time: Optional[datetime] = None


class ChallengeResponse(BaseModel):
    user_id: ObjectIdPydantic
    title: str
    description: str
    metric: str
    limit_time: Optional[datetime] = None
    state: str
    list_multimedia: list[str]
    list_goals: Optional[list[str]]


class UpdateChallenge(BaseModel):
    description: Optional[str] = None
    multimedia: list[str] = []


class Challenge(BaseModel):
    def __init__(
        self,
        user_id,
        title,
        description,
        metric,
        limit,
    ):
        self.user_id = user_id
        self.title = title
        self.description = description
        self.metric = metric
        self.limit = limit
        self.multimedia = []
        self.state = State.NOT_INIT
        self.goals = []

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "603e38915fc3ab182c67b2f9",
                "user_id": "609c962ba85e2101a9b14b55",
                "title": "Reto de 10,000 pasos diarios",
                "description": "Caminar al menos 10,000 pasos todos los días.",
                "metric": "distancia",
                "limit": "2023-12-31",
                "multimedia": [],
                "state": "INIT",
                "goals": ["603e3a4f5fc3ab182c67b2fa", "603e3a5a5fc3ab182c67b2fb"],
            }
        }
