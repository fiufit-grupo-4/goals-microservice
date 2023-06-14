import logging
from logging.config import dictConfig
from os import environ
from pydantic import BaseSettings

from app.log_config import logconfig

dictConfig(logconfig)
logger = logging.getLogger('app')


class Settings(BaseSettings):
    jwt_secret: str = environ.get("JWT_SECRET", "123456")
    jwt_algorithm: str = environ.get("JWT_ALGORITHM", "HS256")
    USER_SERVICE_URL: str = environ.get('USER_SERVICE_URL', 'http:/user-microservice:7501')

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
