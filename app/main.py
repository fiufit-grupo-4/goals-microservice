from fastapi import FastAPI
from app.controller_example import router as example_router
import pymongo
import logging
from logging.config import dictConfig
from .log_config import logconfig
from os import environ

MONGODB_URI = environ["MONGODB_URI"]

dictConfig(logconfig)
app = FastAPI()
logger = logging.getLogger('app')

# Logging examples
# logger.error("Error message! - Level 3")
# logger.warning("Warning message! - Level 2")
# logger.info("Info message! - Level 1")
# logger.debug("Debug message! - Level 0")


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


app.include_router(example_router)
