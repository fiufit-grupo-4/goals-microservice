from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from app.models.challenge import ChallengeCreate, ChallengeResponse
from app.auth.auth_utils import decode_token, get_token_from_header

router_challenge = APIRouter()


@router_challenge.post("/", response_model=ChallengeResponse)
async def create_challenge(request: Request,
                           challenge: ChallengeCreate,
                           authorization: str = Depends(get_token_from_header)):
    challenges = request.app.database["challenges"]
    # Obtener el ID del usuario del token
    user_id = decode_token(authorization)["id"]

    # Crear un nuevo desafío en la base de datos
    new_challenge = {
        "user_id": user_id,
        "title": challenge.title,
        "description": challenge.description,
        "metric": challenge.metric,
        "limit_time": challenge.limit_time or None,
        "state": "NO_INICIADA",
        "list_multimedia": [],
        "list_goals": []
    }
    challenge_id = await challenges.insert_one(new_challenge)

    # Construir la respuesta del desafío creado
    response = ChallengeResponse(
        id=str(challenge_id.inserted_id),
        user_id=user_id,
        title=challenge.title,
        description=challenge.description,
        metric=challenge.metric,
        limit_time=challenge.limit_time,
        state="NO_INICIADA",
        list_multimedia=[],
        list_goals=[]
    )

    return response


@router_challenge.patch("/{id_challenge}")
async def update_challenge(id_challenge: str):
    # Lógica para actualizar un desafío existente
    pass


@router_challenge.delete("/{id_challenge}")
async def delete_challenge(id_challenge: str):
    # Lógica para eliminar un desafío existente
    pass


@router_challenge.get("/{id_challenge}")
async def get_challenge(id_challenge: str):
    # Lógica para obtener un desafío específico
    pass


@router_challenge.get("/")
async def get_challenges():
    # Lógica para obtener todos los desafíos del atleta
    pass


@router_challenge.patch("/{id_challenge}/goals")
async def add_goal_to_challenge(id_challenge: str):
    # Lógica para agregar una meta a un desafío
    pass
