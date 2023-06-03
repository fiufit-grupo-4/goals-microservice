from pydantic import BaseModel, Field


class Goal(BaseModel):
    id: str = Field(..., alias="_id")
    metric: str
    state: str = "NO_INICIADA"
    training_id: str = None
    user_id: str = None

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "603e3a4f5fc3ab182c67b2fa",
                "metric": "distancia",
                "state": "INICIADA",
                "training_id": "609c97f3a85e2101a9b14b57",
                "user_id": "609c962ba85e2101a9b14b55",
            }
        }
