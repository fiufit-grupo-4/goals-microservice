import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from app.config import get_settings
from bson import ObjectId as BaseObjectId

oauth2_scheme = HTTPBearer()


class ObjectIdPydantic(str):
    """Creating a ObjectId class for pydantic models."""

    @classmethod
    def validate(cls, value):
        """Validate given str value to check if good for being ObjectId."""
        try:
            return BaseObjectId(str(value))
        except Exception as e:
            raise ValueError("Not a valid user ID") from e

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


def decode_token(token: str) -> dict:
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )


def get_token_from_header(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ")[1]
