from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from starlette import status
from starlette.responses import JSONResponse
from firebase_admin import messaging
from datetime import datetime, timezone
import dateutil.parser as parser

from app.config.config import logger
from app.models.goal import (
    GoalTypes,
    State,
    UpdateProgressGoal,
)
from app.auth.auth_utils import get_user_id, ObjectIdPydantic
from app.services.services import ServiceUsers, ServiceTrainers

router_goal_states = APIRouter()

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


@router_goal_states.patch("/progress_steps", status_code=status.HTTP_200_OK)
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


@router_goal_states.patch("/{id_goal}/start", status_code=status.HTTP_200_OK)
async def start_goal(request: Request, id_goal: ObjectIdPydantic):
    return await update_state_goal(id_goal, request, State.INIT)


@router_goal_states.patch("/{id_goal}/complete", status_code=status.HTTP_200_OK)
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


@router_goal_states.patch("/{id_goal}/stop", status_code=status.HTTP_200_OK)
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
