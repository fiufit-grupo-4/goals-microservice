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
from app.services.services import NotificationService, ServiceUsers, ServiceTrainers

router_goal_states = APIRouter()


def step_to_calorie(step):
    calories = step * 0.04
    return calories


def step_to_kilometer(step):
    meters = step * 0.76
    kilometers = meters / 1000
    return kilometers


@router_goal_states.patch("/progress_steps", status_code=status.HTTP_200_OK)
async def progress_steps_all_goal(
    request: Request,
    update_data: UpdateProgressGoal,
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]
    query = {"user_id": str(user_id)}

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
            elif goal["metric"] == GoalTypes.CALORIES.value:
                goal["progress_steps"] += step_to_calorie(update_data.progress_steps)
            else:
                goal["progress_steps"] += update_data.progress_steps

            if goal["progress_steps"] >= goal["quantity_steps"]:
                await complete_goal(request, goal["_id"], user_id)

            goals.update_one(
                {"_id": goal["_id"]},
                {"$set": {"progress_steps": goal["progress_steps"]}},
            )

    return {"message": "All goals have been successfully updated"}


@router_goal_states.patch("/{id_goal}/start", status_code=status.HTTP_200_OK)
async def start_goal(request: Request, id_goal: ObjectIdPydantic):
    return await update_state_goal(id_goal, request, State.INIT)


async def complete_goal(request, id_goal, id_user):
    goals = request.app.database["goals"]
    goal = goals.find_one({"_id": id_goal})
    res = await update_state_goal(id_goal, request, State.COMPLETE)
    logger.info(f'Goal completed: {res.status_code}')
    headers = request.headers

    if training_id := goal.get('training_id'):
        await ServiceTrainers.patch(
            f'/athletes/me/trainings/{training_id}/complete',
            json={},
            headers={"authorization": headers["authorization"]},
        )

    await NotificationService.send_notification_completed(request, id_user, goal)
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
            content=f'Goal {id_goal} not found',
        )
    logger.info(f'Updating goal state: {state.name}')

    now_time = datetime.now(timezone.utc)
    if (
        goal["limit"] is not None
        and parser.parse(str(goal["limit"])).replace(tzinfo=timezone.utc) < now_time
    ):
        result_update = goals.update_one(
            {"_id": goal["_id"]}, {"$set": {"state": State.EXPIRED.value}}
        )
    elif state == State.INIT.value and goal["state"] != State.INIT.value:
        result_update = goals.update_one(
            {"_id": id_goal}, {"$set": {"date_init": now_time, "state": state}}
        )
    elif state == State.STOP.value and goal["state"] == State.COMPLETE.value:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f'Goal {id_goal} already completed',
        )
    elif state == State.COMPLETE.value and goal["state"] != State.COMPLETE.value:
        result_update = goals.update_one(
            {"_id": id_goal}, {"$set": {"date_complete": now_time, "state": state}}
        )
    elif state == State.STOP.value and goal["state"] == State.NOT_INIT.value:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f'Goal {id_goal} not started',
        )
    else:
        result_update = goals.update_one({"_id": id_goal}, {"$set": {"state": state}})

    if result_update.modified_count > 0:
        logger.info(f'Updating goal {id_goal} to state {state} successfully')
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
