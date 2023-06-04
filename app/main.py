from fastapi import FastAPI
import pymongo
from os import environ

from .config import logger
from .urls import api_router

MONGODB_URI = environ["MONGODB_URI"]
app = FastAPI()


@app.on_event("startup")
async def startup_db_client():
    try:
        app.mongodb_client = pymongo.MongoClient(MONGODB_URI)
        logger.info("Connected successfully MongoDB")

    except Exception as e:
        logger.error(e)
        logger.error("Could not connect to MongoDB")

    app.logger = logger
    # Build a collection
    app.database = app.mongodb_client["goals_microservice"]
    # collection = db.goals_microservice

    # Clear collection data
    # collection.delete_many({})


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()
    logger.info("Shutdown APP")


app.include_router(api_router)
