import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = os.getenv("JWT_SECRET", "develop")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
