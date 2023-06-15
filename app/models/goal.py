from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class State(Enum):
    NOT_INIT = 1
    INIT = 2
    COMPLETE = 3
    STOP = 4


class RequestUpdateStateGoal(BaseModel):
    state: Optional[int] = State.NOT_INIT
    id_goal: Optional[str]
    progress: Optional[int] = 0


class GoalCreate(BaseModel):
    traning_id: Optional[str]
    title: str
    description: str
    metric: str
    quantity: int
    limit_time: Optional[datetime] = None
    date_init: Optional[datetime] = None
    state: Optional[int] = State.INIT


class GoalResponse(BaseModel):
    id: str
    user_id: Optional[str]
    traning_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    metric: Optional[str]
    limit_time: Optional[datetime]
    date_init: Optional[datetime]
    date_complete: Optional[datetime]
    state: Optional[int]
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
    quantity: Optional[int]
    progress: Optional[int]


class UpdateGoalState(BaseModel):
    state: State


class QueryParamFilterGoal(BaseModel):
    title: Optional[str]
    description: Optional[str]


class Goal:
    def __init__(self,
                 user_id,
                 traning_id: Optional[str],
                 title,
                 description,
                 metric,
                 limit,
                 state: Optional[int] = State.NOT_INIT,
                 quantity: Optional[int] = 0,
                 date_init: Optional[datetime] = None,
                 ):
        self.user_id = user_id
        self.traning_id = traning_id
        self.title = title
        self.description = description
        self.metric = metric
        self.limit = limit
        self.state = state
        self.quantity = quantity
        self.progress = 0
        self.date_init = date_init
        self.date_complete = None
