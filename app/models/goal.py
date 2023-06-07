from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class State(Enum):
    NOT_INIT = 1
    INIT = 2
    COMPLETE = 3


class GoalCreate(BaseModel):
    title: str
    description: str
    metric: str
    limit_time: Optional[datetime] = None
    quantity: int = 0
    progress: int = 0


class GoalResponse(BaseModel):
    id: str
    user_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    metric: Optional[str]
    limit_time: Optional[datetime]
    state: Optional[State]
    list_multimedia: Optional[list]
    quantity: Optional[int]
    progress: Optional[int]

    @classmethod
    def from_mongo(cls, goal):
        if not goal:
            return goal
        id_goal = str(goal.pop('_id', None))
        title = goal.pop('title', None)
        description = goal.pop('description', None)

        goal_dict = {
            **goal,
            'id': id_goal,
            'title': title,
            'description': description,
        }
        return cls(**goal_dict)


class UpdateGoal(BaseModel):
    title: Optional[str]
    description: Optional[str]
    multimedia: Optional[list]
    quantity: Optional[int]
    progress: Optional[int]


class QueryParamFilterGoal(BaseModel):
    title: Optional[str]
    description: Optional[str]


class Goal:
    def __init__(self, user_id, title, description, metric, limit, quantity):
        self.user_id = user_id
        self.title = title
        self.description = description
        self.metric = metric
        self.limit = limit
        self.multimedia = []
        self.state = State.NOT_INIT
        self.quantity = quantity
        self.progress = 0

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "603e38915fc3ab182c67b2f9",
                "user_id": "609c962ba85e2101a9b14b55",
                "title": "Reto de 50K a fin de anio",
                "description": "Correr la mararon de 50K a fin de anio",
                "metric": "distancia",
                "limit": "2023-12-31",
                "multimedia": [],
                "state": 1,  # NOT_INIT
                "quantity": 50,
                "progress": 0,
            }
        }
