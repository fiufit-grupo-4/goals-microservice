from fastapi import HTTPException
import httpx
import app.main as main
from starlette import status
from os import environ
from firebase_admin import messaging

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

    @staticmethod
    async def patch(path, json, headers):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{USER_SERVICE_URL}{path}",
                    json=json,
                    headers=headers,
                )
                return response
        except Exception:
            main.logger.error('User service cannot be accessed')
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
                    f"{TRAINING_SERVICE_URL}{path}",
                    json=json,
                    headers=headers,
                )
                return response
        except Exception:
            main.logger.error('Training service cannot be accessed')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Training service cannot be accessed',
            )


class NotificationService:
    def send_push_notification(device_token, title, body):
        if device_token is not None:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=device_token,
            )
            messaging.send(message)

    async def get_device_token(user_id):
        user = await ServiceUsers.get(f'/users/{user_id}')
        if user.status_code == 200:
            user = user.json()
            return user.pop('device_token')

    async def send_notification_completed(request, user_id, goal):
        token = await NotificationService.get_device_token(str(user_id))
        NotificationService.send_push_notification(
            device_token=token,
            title='Goal accomplished',
            body=f"Completaste la meta {goal['title']}",
        )
        await ServiceUsers.patch(
            f'/users/{str(user_id)}',
            json={
                "notifications": {
                    "title": 'Goal accomplished',
                    "body": f"Completaste la meta {goal['title']}",
                }
            },
            headers={"authorization": request.headers["authorization"]},
        )
