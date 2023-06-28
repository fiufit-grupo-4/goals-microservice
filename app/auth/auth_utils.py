from os import environ
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from app.auth.auth_bearer import JWTBearer
from app.config.config import get_settings
from app.models.goal import UserRoles
from bson import ObjectId

from datetime import timedelta, datetime

oauth2_scheme = HTTPBearer()
RESET_PASSWORD_EXPIRATION_MINUTES = environ.get("RESET_PASSWORD_EXPIRATION_MINUTES", 60)
EXPIRES = timedelta(minutes=int(RESET_PASSWORD_EXPIRATION_MINUTES))
JWT_SECRET = environ.get("JWT_SECRET", "123456")
JWT_ALGORITHM = environ.get("JWT_ALGORITHM", "HS256")


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
        settings = get_settings()
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=settings.jwt_algorithm
        )
        return ObjectId(payload["id"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )


def generate_token_with_role(id: str, role: UserRoles) -> str:
    utcnow = datetime.utcnow()
    expires = utcnow + EXPIRES
    token_data = {"id": id, "exp": expires, "iat": utcnow, "role": role}
    token = jwt.encode(token_data, key=JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token
