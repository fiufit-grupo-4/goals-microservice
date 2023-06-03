from typing import List
from pydantic import BaseModel, Field

class Challenge(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    title: str
    description: str
    metric: str
    limit: str = None
    multimedia: List[str] = []
    state: str = "NO_INICIADA"
    goals: List[str] = []

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "603e38915fc3ab182c67b2f9",
                "user_id": "609c962ba85e2101a9b14b55",
                "title": "Reto de 10,000 pasos diarios",
                "description": "Caminar al menos 10,000 pasos todos los días.",
                "metric": "distancia",
                "limit": "2023-12-31",
                "multimedia": [],
                "state": "INICIADA",
                "goals": ["603e3a4f5fc3ab182c67b2fa", "603e3a5a5fc3ab182c67b2fb"]
            }
        }
