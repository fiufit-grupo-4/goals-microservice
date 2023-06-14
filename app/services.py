from fastapi import HTTPException
import httpx
import app.main as main
from starlette import status
from config import Settings


class ServiceUsers:
    @staticmethod
    async def get(path):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(Settings.USER_SERVICE_URL + path)
                return response
        except Exception:
            main.logger.error('User service cannot be accessed')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='User service cannot be accessed',
            )
