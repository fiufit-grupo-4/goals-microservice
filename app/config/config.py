from dotenv import load_dotenv
from logging.config import dictConfig
from os import environ
from pydantic import BaseSettings
from app.config.log_config import logconfig
from datetime import timedelta
import logging

load_dotenv()
dictConfig(logconfig)
logger = logging.getLogger('app')


class Settings(BaseSettings):
    MONGODB_URI: str = environ.get("MONGODB_URI", "mongodb:27017")
    JWT_SECRET: str = environ.get("JWT_SECRET", "123456")
    JWT_ALGORITHM: str = environ.get("JWT_ALGORITHM", "HS256")
    RESET_PASSWORD_EXPIRATION_MINUTES = environ.get(
        "RESET_PASSWORD_EXPIRATION_MINUTES", 60
    )
    EXPIRES = timedelta(minutes=int(RESET_PASSWORD_EXPIRATION_MINUTES))
    USER_SERVICE_URL: str = environ.get(
        'USER_SERVICE_URL', 'http://user-microservice:7500'
    )
    TRAINING_SERVICE_URL = environ.get(
        'TRAINING_SERVICE_URL', 'http://training-microservice:7501'
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
