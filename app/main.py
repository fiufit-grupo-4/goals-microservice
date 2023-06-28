from fastapi import FastAPI
import pymongo
from app.config.config import logger, Settings
from app.routes.urls import api_router

app = FastAPI()
app_settings = Settings()


@app.on_event("startup")
async def startup_db_client():
    try:
        app.mongodb_client = pymongo.MongoClient(app_settings.MONGODB_URI)
        logger.info("Connected successfully MongoDB")
    except Exception as e:
        logger.error(e)
        logger.error("Could not connect to MongoDB")

    app.logger = logger
    app.database = app.mongodb_client["goals_microservice"]


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()
    logger.info("Shutdown APP")


app.include_router(api_router)
