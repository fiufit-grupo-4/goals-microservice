from http.client import HTTPException

from bson import ObjectId
from fastapi import APIRouter, Depends, Request, Query
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import JSONResponse

from app.config import logger
from app.models.goal import (
    GoalCreate,
    GoalResponse,
    Goal,
    UpdateGoal,
    QueryParamFilterGoal,
)
from app.auth.auth_utils import get_user_id, ObjectIdPydantic

router_goal = APIRouter()


@router_goal.post("/", response_model=GoalResponse)
async def create_challenge(
    request: Request,
    goal: GoalCreate,
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]

    # Crear un nuevo desafío en la base de datos
    new_goal = Goal(
        user_id=str(user_id),
        title=goal.title,
        description=goal.description,
        metric=goal.metric,
        limit=goal.limit_time,
        quantity=goal.quantity,
    )
    challenge_id = goals.insert_one(jsonable_encoder(new_goal))

    # Construir la respuesta del desafío creado
    response = GoalResponse(
        id=str(challenge_id.inserted_id),
        user_id=new_goal.user_id,
        title=new_goal.title,
        description=new_goal.description,
        metric=new_goal.metric,
        limit_time=new_goal.limit,
        state=new_goal.state,
        list_multimedia=new_goal.multimedia,
        quantity=new_goal.quantity,
        progress=new_goal.progress,
    )

    return response


@router_goal.patch("/{id_goal}")
async def update_challenge(
    request: Request, id_goal: ObjectIdPydantic, update_data: UpdateGoal
):
    to_change = update_data.dict(exclude_none=True)

    if not to_change or len(to_change) == 0:
        logger.info('No values specified in body to update')
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content='No values specified to update',
        )

    goals = request.app.database["goals"]
    # Obtener el desafío existente de la base de datos
    goal = goals.find_one({"_id": id_goal})

    if not goal:
        logger.info(f'User {id_goal} not found to update')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'User {id_goal} not found',
        )

    if update_data.description is not None:
        goal["description"] = update_data.description

    if update_data.multimedia:
        goal["list_multimedia"].extend(update_data.multimedia)

    result_update = goals.update_one({"_id": id_goal}, {"$set": goal})

    if result_update.modified_count > 0:
        logger.info(f'Updating user {id_goal} a values of {list(to_change.keys())}')
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=f'User {id_goal} updated successfully',
        )
    else:
        logger.info(f'User {id_goal} not updated')
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f'User {id_goal} not updated',
        )


@router_goal.delete("/{id_goal}")
async def delete_challenge(id_goal: ObjectIdPydantic, request: Request):
    goals = request.app.database["goals"]
    result = goals.delete_one({"_id": ObjectId(id_goal)})

    if result.deleted_count == 1:
        logger.info(f'Deleting user {id_goal}')
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=f'User {id_goal} deleted successfully',
        )
    else:
        logger.info(f'User {id_goal} not found to delete')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'User {id_goal} not found to delete',
        )


@router_goal.get("/{id_goal}")
async def get_challenge(id_goal: ObjectIdPydantic, request: Request):
    goals = request.app.database["goals"]
    goal = goals.find_one({"_id": id_goal})

    if goal:
        return GoalResponse.from_mongo(goal)
    else:
        logger.info(f'User {id_goal} not found to get')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'User {id_goal} not found to get',
        )


@router_goal.get("/")
async def get_goals(
    request: Request,
    queries: QueryParamFilterGoal = Depends(),
    limit: int = Query(128, ge=1, le=1024),
):
    goals = request.app.database["goals"]

    query = queries.dict(exclude_none=True)

    all_goals = []
    for goal in goals.find(query).limit(limit):
        if res := GoalResponse.from_mongo(goal):
            all_goals.append(res)

    return all_goals
