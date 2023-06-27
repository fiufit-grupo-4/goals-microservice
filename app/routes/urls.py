from fastapi import APIRouter

from app.routes.goal_crud import router_goal_crud
from app.routes.goal_states import router_goal_states

api_router = APIRouter()

api_router.include_router(
    router_goal_states, tags=["Goals for Athletes - Goals microservice"], prefix="/athletes/me/goals"
)

api_router.include_router(
    router_goal_crud, tags=["CRUD for Athletes - Goals microservice"], prefix="/athletes/me/goals"
)
