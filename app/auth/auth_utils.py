import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from app.auth.auth_bearer import JWTBearer
from app.config import get_settings
from bson import ObjectId

from app.main import logger

oauth2_scheme = HTTPBearer()


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
        logger.info("token:" + token)
        settings = get_settings()
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        logger.info(payload)
        return ObjectId(payload["id"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )
