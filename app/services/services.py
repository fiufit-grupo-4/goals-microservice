from fastapi import HTTPException
import httpx
from app.config.config import Settings
import app.main as main
from starlette import status

app_settings = Settings()


class ServiceUsers:
    @staticmethod
    async def get(path):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    app_settings.USER_SERVICE_URL + path + '?map_trainings=false'
                )
                return response
        except Exception:
            main.logger.error(
                f'User service cannot be accessed for {app_settings.USER_SERVICE_URL + path}'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='User service cannot be accessed',
            )

    @staticmethod
    async def patch(path, json, headers):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{app_settings.USER_SERVICE_URL}{path}",
                    json=json,
                    headers=headers,
                )
                return response
        except Exception:
            main.logger.error(
                f'User service cannot be accessed for {app_settings.USER_SERVICE_URL}{path}'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='User service cannot be accessed',
            )

    @staticmethod
    async def post(path, json, headers):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{app_settings.USER_SERVICE_URL}{path}",
                    json=json,
                    headers=headers,
                )
                return response
        except Exception as e:
            main.logger.error(
                f'User service cannot be accessed for {app_settings.USER_SERVICE_URL}{path} with error: {e}'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='User service cannot be accessed',
            )


class ServiceTrainers:
    @staticmethod
    async def patch(path, json, headers):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{app_settings.TRAINING_SERVICE_URL}{path}",
                    json=json,
                    headers=headers,
                )
                return response
        except Exception:
            main.logger.error(
                f'Training service cannot be accessed for {app_settings.TRAINING_SERVICE_URL}{path}'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Training service cannot be accessed',
            )


class NotificationService:
    async def send_notification_completed(request, user_id, goal):
        json = {
            "id_receiver": str(user_id),
            "title_goal": goal['title'],
        }
        response = await ServiceUsers.post(
            '/notifications/goal/completed/send', json=json, headers={}
        )

        if response.status_code != 200:
            main.logger.error(f'Error sending notification to user {str(user_id)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Error in system notification',
            )
