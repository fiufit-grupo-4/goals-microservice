from fastapi import HTTPException
import httpx
import app.main as main
from starlette import status
from os import environ

USER_SERVICE_URL = environ.get('USER_SERVICE_URL', 'http://user-microservice:7501')
TRAINING_SERVICE_URL = environ.get(
    'TRAINING_SERVICE_URL', 'http://training-microservice:7501'
)


class ServiceUsers:
    @staticmethod
    async def get(path):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(USER_SERVICE_URL + path)
                return response
        except Exception:
            main.logger.error('User service cannot be accessed')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='User service cannot be accessed',
            )


class ServiceTrainers:
    @staticmethod
    async def get(path):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(TRAINING_SERVICE_URL + path)
                return response
        except Exception:
            main.logger.error('Training service cannot be accessed')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Training service cannot be accessed',
            )
