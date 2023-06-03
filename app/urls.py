from fastapi import APIRouter

from app.routes.challenge import router_challenge

api_router = APIRouter()
@api_router.get("/", tags=["Home"])
def get_root() -> dict:
    return {"message": "OK"}

api_router.include_router(router_challenge, tags=["Athletes Challenges"], prefix="/athletes/me/challenges")