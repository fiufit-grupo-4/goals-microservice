from fastapi import APIRouter

router = APIRouter(tags=["Example"])


@router.get("/example")
async def get_example() -> dict:
    return {"message": "soy un ejemplo 2"}
