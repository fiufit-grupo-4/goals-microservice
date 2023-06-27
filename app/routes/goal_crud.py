from bson import ObjectId
from fastapi import APIRouter, Depends, Request, Query
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import JSONResponse
from datetime import datetime, timezone
import dateutil.parser as parser

from app.models.goal import (
    GoalCreate,
    GoalResponse,
    Goal,
    UpdateGoal,
    State,
)
from app.auth.auth_utils import get_user_id, ObjectIdPydantic
from app.config.config import logger

router_goal_crud = APIRouter()

@router_goal_crud.post("/", response_model=GoalResponse)
async def create_goal(
    request: Request,
    goal: GoalCreate,
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]
    # Crear un nuevo desafío en la base de datos
    new_goal = Goal(
        user_id=str(user_id),
        training_id=goal.training_id,
        title=goal.title,
        description=goal.description,
        metric=goal.metric,
        limit=goal.limit_time,
        state=goal.state,
        quantity_steps=goal.quantity_steps,
    )

    time_now = datetime.now(timezone.utc)

    if goal.training_id is not None:
        new_goal.training_id = goal.training_id
        new_goal.state = State.INIT.value
        new_goal.date_init = time_now

    res_json = jsonable_encoder(new_goal)

    if res_json["limit"] is not None:
        res_json["limit"] = parser.parse(res_json["limit"]).replace(tzinfo=timezone.utc)
        if res_json["limit"] < time_now:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Limit date is before current date"},
            )

    if res_json["date_init"] is not None:
        res_json["date_init"] = parser.parse(res_json["date_init"]).replace(
            tzinfo=timezone.utc
        )
        if res_json["date_init"] < time_now:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Date init is before current date"},
            )

    goal_id = goals.insert_one(res_json)

    # Construir la respuesta del desafío creado
    response = GoalResponse(
        id=str(goal_id.inserted_id),
        user_id=new_goal.user_id,
        training_id=new_goal.training_id,
        title=new_goal.title,
        description=new_goal.description,
        metric=new_goal.metric,
        limit_time=new_goal.limit,
        date_init=new_goal.date_init,
        date_complete=None,
        state=new_goal.state,
        quantity_steps=new_goal.quantity_steps,
        progress_steps=new_goal.progress_steps,
    )

    return response


@router_goal_crud.get("/", status_code=status.HTTP_200_OK)
async def get_my_goals(
    request: Request,
    limit: int = Query(128, ge=1, le=1024),
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]

    # Filtrar por el user_id específico
    query = {"user_id": str(user_id)}

    all_goals = []
    for goal in goals.find(query).limit(limit):
        logger.info(goal)
        if res := GoalResponse.from_mongo(goal):
            all_goals.append(res)

    return all_goals


@router_goal_crud.get("/{id_goal}", status_code=status.HTTP_200_OK)
async def get_goal(id_goal: ObjectIdPydantic, request: Request):
    goals = request.app.database["goals"]
    goal = goals.find_one({"_id": id_goal})

    if goal:
        return GoalResponse.from_mongo(goal)
    else:
        logger.info(f'Goal {id_goal} not found to get')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'Goal {id_goal} not found to get',
        )

@router_goal_crud.patch("/{id_goal}", status_code=status.HTTP_200_OK)
async def update_goal(
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
    goal = goals.find_one({"_id": id_goal})

    time_now = datetime.now(timezone.utc)
    if to_change["limit_time"] is not None:
        to_change["limit_time"] = parser.parse(str(to_change["limit_time"])).replace(
            tzinfo=timezone.utc
        )
        if to_change["limit_time"] < time_now:
            logger.error(f"LIMIT TIME: {to_change['limit_time']} AND NOW: {time_now}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Limit date is before current date"},
            )
        to_change["limit"] = to_change["limit_time"]
        to_change.pop("limit_time")

        if goal["state"] == State.EXPIRED.value:
            to_change["state"] = State.NOT_INIT.value
            to_change["progress_steps"] = 0
            to_change["date_init"] = None

    if not goal:
        logger.info(f'Goal {id_goal} not found to update')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'Goal {id_goal} not found',
        )

    goals.update_one({"_id": id_goal}, {"$set": to_change})

    return {"message": "Goal updated successfully"}


@router_goal_crud.delete("/{id_goal}", status_code=status.HTTP_200_OK)
async def delete_goal(id_goal: ObjectIdPydantic, request: Request):
    goals = request.app.database["goals"]
    result = goals.delete_one({"_id": ObjectId(id_goal)})

    if result.deleted_count == 1:
        logger.info(f'Deleting Goal {id_goal}')
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=f'Goal {id_goal} deleted successfully',
        )
    else:
        logger.info(f'Goal {id_goal} not found to delete')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'Goal {id_goal} not found to delete',
        )
