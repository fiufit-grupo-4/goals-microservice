from fastapi import APIRouter

from app.routes.goal import router_goal

api_router = APIRouter()


@api_router.get("/", tags=["Home"])
def get_root() -> dict:
    return {"message": "OK"}


api_router.include_router(router_goal, tags=["Athletes Goals"], prefix="/athletes/me/goals")
