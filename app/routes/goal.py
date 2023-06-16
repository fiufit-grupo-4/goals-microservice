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
    State,
    UpdateProgressGoal,
)
from app.auth.auth_utils import get_user_id, ObjectIdPydantic

router_goal = APIRouter()


### Create new goal ###
@router_goal.post("/", response_model=GoalResponse, status_code=status.HTTP_200_OK)
async def create_goal(
    request: Request,
    goal: GoalCreate,
    user_id: ObjectId = Depends(get_user_id),
):
    goals = request.app.database["goals"]
    # Crear un nuevo desafío en la base de datos
    logger.info(goal.json())
    new_goal = Goal(
        user_id=str(user_id),
        traning_id=goal.traning_id,
        title=goal.title,
        description=goal.description,
        metric=goal.metric,
        limit=goal.limit_time,
        state=goal.state,
        quantity=goal.quantity,
    )

    if goal.traning_id is not None:
        new_goal.traning_id = goal.traning_id
        new_goal.state = State.NOT_INIT.value
        new_goal.date_init = goal.date_init

    goal_id = goals.insert_one(jsonable_encoder(new_goal))

    # Construir la respuesta del desafío creado
    response = GoalResponse(
        id=str(goal_id.inserted_id),
        user_id=new_goal.user_id,
        traning_id=new_goal.traning_id,
        title=new_goal.title,
        description=new_goal.description,
        metric=new_goal.metric,
        limit_time=new_goal.limit,
        date_init=new_goal.date_init,
        date_complete=new_goal.date_complete,
        state=new_goal.state,
        quantity=new_goal.quantity,
        progress=new_goal.progress,
    )

    return response


### Select own goal ###
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
    goals = request.app.database["goals"]
    # Obtener el desafío existente de la base de datos
    goal = goals.find_one({"_id": id_goal})

    if not goal:
        logger.info(f'Goal {id_goal} not found to update')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'Goal {id_goal} not found',
        )
    goal["progress"] = goal["progress"] + update_data.progress

    if goal["progress"] >= goal["quantity"]:
        await complete_goal(request, id_goal)

    goals.update_one({"_id": id_goal}, {"$set": goal})

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


@router_goal.patch("/{id_goal}/progress", status_code=status.HTTP_200_OK)
async def progress_goal(
    request: Request, id_goal: ObjectIdPydantic, update_data: UpdateProgressGoal
):
    goals = request.app.database["goals"]
    # Obtener el desafío existente de la base de datos
    goal = goals.find_one({"_id": id_goal})

    if not goal:
        logger.info(f'Goal {id_goal} not found to update')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f'Goal {id_goal} not found',
        )
    goal["progress"] = goal["progress"] + update_data.progress

    if goal["progress"] >= goal["quantity"]:
        await complete_goal(request, id_goal)

    goals.update_one({"_id": id_goal}, {"$set": goal})

    return {"message": "Goal updated successfully"}


@router_goal.patch("/{id_goal}/start", status_code=status.HTTP_200_OK)
async def start_goal(request: Request, id_goal: ObjectIdPydantic):
    return await update_state_goal(id_goal, request, State.INIT)


@router_goal.patch("/{id_goal}/complete", status_code=status.HTTP_200_OK)
async def complete_goal(request: Request, id_goal: ObjectIdPydantic):
    return await update_state_goal(id_goal, request, State.COMPLETE)


@router_goal.patch("/{id_goal}/stop", status_code=status.HTTP_200_OK)
async def complete_goal(request: Request, id_goal: ObjectIdPydantic):
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

    update_data = {"state": state.value}
    result_update = goals.update_one({"_id": id_goal}, {"$set": update_data})

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
