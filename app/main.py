import firebase_admin
from fastapi import FastAPI
import pymongo
from os import environ
from firebase_admin import credentials
from app.config.credentials import firebase_credentials
from app.config.config import logger
from app.routes.urls import api_router

app = FastAPI()
firebase_admin.initialize_app(credentials.Certificate(firebase_credentials))


@app.on_event("startup")
async def startup_db_client():
    try:
        app.mongodb_client = pymongo.MongoClient(environ["MONGODB_URI"])
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
