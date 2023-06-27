from bson import ObjectId
from fastapi import APIRouter, Depends, Request, Query
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import JSONResponse
from firebase_admin import messaging
from datetime import datetime, timezone
import dateutil.parser as parser

from app.config import logger
from app.models.goal import (
    GoalCreate,
    GoalResponse,
    Goal,
    GoalTypes,
    UpdateGoal,
    State,
    UpdateProgressGoal,
)
from app.auth.auth_utils import get_user_id, ObjectIdPydantic
from app.services import ServiceUsers, ServiceTrainers

router_goal = APIRouter()


def step_to_calorie(step):
    calories = step * 0.04
    return calories


def step_to_kilometer(step):
    meters = step * 0.76
    kilometers = meters / 1000
    return kilometers


def send_push_notification(device_token, title, body):
    if device_token is not None:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=device_token,
        )
        messaging.send(message)


async def get_device_token(user_id):
    user = await ServiceUsers.get(f'users/{user_id}')
    if user.status_code == 200:
        user = user.json()
        return user.pop('device_token')


@router_goal.patch("/progress_steps", status_code=status.HTTP_200_OK)
async def progress_steps_all_goal(
    request: Request,
    update_data: UpdateProgressGoal,
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]
    # Filtrar por el user_id específico
    query = {"user_id": str(user_id)}

    # Actualizar los objetivos encontrados
    for goal in goals.find(query):
        if goal["limit"]:
            if (
                parser.parse(str(goal["limit"])).replace(tzinfo=timezone.utc)
                < datetime.now(timezone.utc)
                and goal["state"] != State.EXPIRED.value
            ):
                goals.update_one(
                    {"_id": goal["_id"]}, {"$set": {"state": State.EXPIRED.value}}
                )
                continue

        if goal["state"] == State.INIT:
            if goal["metric"] == GoalTypes.KILOMETERS.value:
                goal["progress_steps"] += step_to_kilometer(update_data.progress_steps)
            elif goal["metric"] == GoalTypes.STEPS.value:
                goal["progress_steps"] += update_data.progress_steps
            elif goal["metric"] == GoalTypes.CALORIES.value:
                goal["progress_steps"] += step_to_calorie(update_data.progress_steps)

            if goal["progress_steps"] >= goal["quantity_steps"]:
                goal["state"] = State.COMPLETE

                await complete_goal(request, goal["_id"])
                print("----")
                token = await get_device_token(str(user_id))
                send_push_notification(
                    device_token=token,
                    title='Goal accomplished',
                    body=f"Completaste la meta {goal['title']}",
                )
                response = await ServiceUsers.patch(
                    f'users/{str(user_id)}',
                    json={
                        "notifications": {
                            "title": 'Goal accomplished',
                            "body": f"Completaste la meta {goal['title']}",
                        }
                    },
                    headers={"authorization": request.headers["authorization"]},
                )

                print(response.status_code)
                print(response.json())

        goals.update_one({"_id": goal["_id"]}, {"$set": goal})

    return {"message": "Goal updated successfully"}


@router_goal.post("/", response_model=GoalResponse)
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


@router_goal.get("/", status_code=status.HTTP_200_OK)
async def get_me_goals(
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


@router_goal.patch("/{id_goal}", status_code=status.HTTP_200_OK)
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


@router_goal.delete("/{id_goal}", status_code=status.HTTP_200_OK)
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


@router_goal.get("/{id_goal}", status_code=status.HTTP_200_OK)
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


@router_goal.patch("/{id_goal}/start", status_code=status.HTTP_200_OK)
async def start_goal(request: Request, id_goal: ObjectIdPydantic):
    return await update_state_goal(id_goal, request, State.INIT)


@router_goal.patch("/{id_goal}/complete", status_code=status.HTTP_200_OK)
async def complete_goal(
    request: Request,
    id_goal: ObjectIdPydantic,
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]
    goal = goals.find_one({"_id": id_goal})
    await update_state_goal(id_goal, request, State.COMPLETE)
    headers = request.headers

    training_id = goal['training_id']
    if training_id is not None:
        await ServiceTrainers.patch(
            f'/athletes/me/trainings/{training_id}/complete',
            json={},
            headers={"authorization": headers["authorization"]},
        )
    return {"message": "Goal completed successfully"}


@router_goal.patch("/{id_goal}/stop", status_code=status.HTTP_200_OK)
async def stop_goal(request: Request, id_goal: ObjectIdPydantic):
    return await update_state_goal(id_goal, request, State.STOP)


async def update_state_goal(id_goal, request, state):
    goals = request.app.database["goals"]
    goal = goals.find_one({"_id": id_goal})
    if not goal:
        logger.info(f'Goal state {id_goal} not found to update')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'Goal state {id_goal} not found',
        )
    logger.info(f'Updating goal state: {state.name}')

    now_time = datetime.now(timezone.utc)
    if (
        goal["limit"] is not None
        and parser.parse(str(goal["limit"])).replace(tzinfo=timezone.utc) < now_time
    ):
        logger.info('Updating goal state to EXPIRED')
        result_update = goals.update_one(
            {"_id": goal["_id"]}, {"$set": {"state": State.EXPIRED.value}}
        )
    elif state == State.INIT.value:
        logger.info('Updating goal state to INIT')
        result_update = goals.update_one(
            {"_id": id_goal}, {"$set": {"date_init": now_time, "state": state}}
        )
    elif state == State.COMPLETE.value:
        logger.info('Updating goal state to COMPLETE')
        result_update = goals.update_one(
            {"_id": id_goal}, {"$set": {"date_complete": now_time, "state": state}}
        )
    else:
        logger.info(f'Updating goal state to {state}')
        result_update = goals.update_one({"_id": id_goal}, {"$set": {"state": state}})

    if result_update.modified_count > 0:
        logger.info('Updating goal state successfully')
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=f'Goal state {id_goal} updated successfully',
        )
    else:
        logger.info(f'Goal state {id_goal} not updated')
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f'Goal state {id_goal} not updated',
        )
