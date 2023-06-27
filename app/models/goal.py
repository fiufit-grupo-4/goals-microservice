from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class GoalTypes(str, Enum):
    KILOMETERS = "Kilometers"
    STEPS = "Steps"
    CALORIES = "Calories"


class State(int, Enum):
    NOT_INIT = 1
    INIT = 2
    COMPLETE = 3
    STOP = 4
    EXPIRED = 5


class UserRoles(int, Enum):
    ADMIN = 1
    TRAINER = 2
    ATLETA = 3


class GoalCreate(BaseModel):
    training_id: Optional[str]
    title: str
    description: str
    quantity_steps: float
    metric: GoalTypes = GoalTypes.STEPS.value
    limit_time: Optional[datetime] = None
    date_init: Optional[datetime] = None
    state: Optional[int] = State.NOT_INIT.value


class GoalResponse(BaseModel):
    id: str
    user_id: Optional[str]
    training_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    metric: Optional[GoalTypes]
    limit_time: Optional[datetime]
    date_init: Optional[datetime]
    date_complete: Optional[datetime]
    state: Optional[int]
    quantity_steps: Optional[float]
    progress_steps: Optional[float]

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
    metric: Optional[GoalTypes]
    limit_time: Optional[datetime]
    quantity_steps: Optional[float]


class UpdateProgressGoal(BaseModel):
    progress_steps: float


class UpdateGoalState(BaseModel):
    state: State


class QueryParamFilterGoal(BaseModel):
    title: Optional[str]
    description: Optional[str]


class Goal:
    def __init__(
        self,
        user_id,
        training_id: Optional[str],
        title,
        description,
        metric: GoalTypes = GoalTypes.STEPS.value,
        state: Optional[int] = State.NOT_INIT.value,
        quantity_steps: Optional[float] = 0,
        limit: Optional[datetime] = None,
        date_init: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self.training_id = training_id
        self.title = title
        self.description = description
        self.metric = metric
        self.limit = limit
        self.state = state
        self.quantity_steps = quantity_steps
        self.progress_steps = 0
        self.date_init = date_init
