import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from app.auth.auth_bearer import JWTBearer
from app.config.config import Settings
from app.models.goal import UserRoles
from bson import ObjectId

from datetime import datetime

oauth2_scheme = HTTPBearer()
app_settings = Settings()


class ObjectIdPydantic(str):
    """Creating a ObjectId class for pydantic models."""

    @classmethod
    def validate(cls, value):
        """Validate given str value to check if good for being ObjectId."""
        try:
            return ObjectId(str(value))
        except Exception as e:
            raise ValueError("Not a valid user ID") from e

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


def get_user_id(token: str = Depends(JWTBearer())) -> ObjectId:
    try:
        payload = jwt.decode(
            token, app_settings.JWT_SECRET, algorithms=app_settings.JWT_ALGORITHM
        )
        return ObjectId(payload["id"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )


def generate_token_with_role(id: str, role: UserRoles) -> str:
    utcnow = datetime.utcnow()
    expires = utcnow + app_settings.EXPIRES
    token_data = {"id": id, "exp": expires, "iat": utcnow, "role": role}
    token = jwt.encode(
        token_data, key=app_settings.JWT_SECRET, algorithm=app_settings.JWT_ALGORITHM
    )
    return token
