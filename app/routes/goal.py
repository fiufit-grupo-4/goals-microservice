from http.client import HTTPException

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder

from app.models.goal import (
    GoalCreate,
    GoalResponse,
    Goal,
    UpdateGoal,
)
from app.auth.auth_utils import get_user_id

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
        quantity=goal.quantity
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
        progress=new_goal.progress
    )

    return response


@router_goal.patch("/{id_challenge}")
async def update_challenge(
    request: Request, id_challenge: str, update_data: UpdateGoal
):
    challenges = request.app.database["challenges"]
    # Obtener el desafío existente de la base de datos
    existing_challenge = await challenges.find_one({"_id": ObjectId(id_challenge)})

    if existing_challenge is None:
        # El desafío no existe
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Actualizar la descripción del desafío si se proporciona
    if update_data.description is not None:
        existing_challenge["description"] = update_data.description

    # Agregar fotos o videos a la lista multimedia
    if update_data.multimedia:
        existing_challenge["list_multimedia"].extend(update_data.multimedia)

    # Actualizar el desafío en la base de datos
    await challenges.update_one(
        {"_id": ObjectId(id_challenge)}, {"$set": existing_challenge}
    )

    # Construir y retornar la respuesta del desafío actualizado
    response = GoalResponse(
        id=id_challenge,
        user_id=existing_challenge["user_id"],
        title=existing_challenge["title"],
        description=existing_challenge["description"],
        metric=existing_challenge["metric"],
        limit_time=existing_challenge["limit_time"],
        state=existing_challenge["state"],
        list_multimedia=existing_challenge["list_multimedia"],
        list_goals=existing_challenge["list_goals"],
    )
    return response


@router_goal.delete("/{id_challenge}")
async def delete_challenge(id_challenge: str, request: Request):
    challenges = request.app.database["challenges"]

    # Buscar el desafío en la base de datos
    existing_challenge = await challenges.find_one({"_id": ObjectId(id_challenge)})

    if existing_challenge is None:
        # El desafío no existe
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Eliminar el desafío de la base de datos
    await challenges.delete_one({"_id": ObjectId(id_challenge)})

    # Retornar una respuesta exitosa
    return {"message": "Challenge deleted successfully"}


@router_goal.get("/{id_challenge}")
async def get_challenge(id_challenge: str, request: Request):
    challenges = request.app.database["challenges"]

    # Buscar el desafío en la base de datos
    existing_challenge = await challenges.find_one({"_id": ObjectId(id_challenge)})

    if existing_challenge is None:
        # El desafío no existe
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Construir y retornar la respuesta del desafío
    response = GoalResponse(
        id=id_challenge,
        user_id=existing_challenge["user_id"],
        title=existing_challenge["title"],
        description=existing_challenge["description"],
        metric=existing_challenge["metric"],
        limit_time=existing_challenge["limit_time"],
        state=existing_challenge["state"],
        list_multimedia=existing_challenge["list_multimedia"],
        list_goals=existing_challenge["list_goals"],
    )
    return response


@router_goal.get("/")
async def get_challenges(request: Request, user_id: ObjectId = Depends(get_user_id)):
    challenges = request.app.database["challenges"]

    # Obtener todos los desafíos del atleta
    all_challenges = await challenges.find({"user_id": user_id}).to_list(None)

    # Construir y retornar la respuesta con todos los desafíos
    response = [
        GoalResponse(
            id=str(challenge["_id"]),
            user_id=challenge["user_id"],
            title=challenge["title"],
            description=challenge["description"],
            metric=challenge["metric"],
            limit_time=challenge["limit_time"],
            state=challenge["state"],
            list_multimedia=challenge["list_multimedia"],
            list_goals=challenge["list_goals"],
        )
        for challenge in all_challenges
    ]

    return response


@router_goal.patch("/{id_challenge}/goals")
async def add_goal_to_challenge(id_challenge: str, goal_id: str, request: Request):
    challenges = request.app.database["challenges"]
    goals = request.app.database["goals"]

    # Obtener el desafío existente de la base de datos
    existing_challenge = await challenges.find_one({"_id": ObjectId(id_challenge)})
    if existing_challenge is None:
        # El desafío no existe
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Obtener la meta de la base de datos
    goal = await goals.find_one({"_id": ObjectId(goal_id)})
    if goal is None:
        # La meta no existe
        raise HTTPException(status_code=404, detail="Goal not found")

    # Verificar si el tipo de métrica de la meta coincide con el del desafío
    if goal["metric"] != existing_challenge["metric"]:
        raise HTTPException(
            status_code=400, detail="Goal metric does not match challenge metric"
        )

    # Verificar la fecha de finalización de la meta con la fecha de finalización del desafío
    if "limit_time" in existing_challenge and "limit_time" in goal:
        if goal["limit_time"] > existing_challenge["limit_time"]:
            raise HTTPException(
                status_code=400, detail="Goal limit time exceeds challenge limit time"
            )

    # Agregar la meta al desafío
    existing_challenge["list_goals"].append(goal)

    # Actualizar el desafío en la base de datos
    await challenges.update_one(
        {"_id": ObjectId(id_challenge)}, {"$set": existing_challenge}
    )

    # Construir y retornar la respuesta actualizada del desafío
    response = GoalResponse(
        id=id_challenge,
        user_id=existing_challenge["user_id"],
        title=existing_challenge["title"],
        description=existing_challenge["description"],
        metric=existing_challenge["metric"],
        limit_time=existing_challenge["limit_time"],
        state=existing_challenge["state"],
        list_multimedia=existing_challenge["list_multimedia"],
        list_goals=existing_challenge["list_goals"],
    )
    return response
