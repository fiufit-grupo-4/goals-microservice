from fastapi import APIRouter

api_router = APIRouter()
@api_router.get("/", tags=["Home"])
def get_root() -> dict:
    return {"message": "OK"}