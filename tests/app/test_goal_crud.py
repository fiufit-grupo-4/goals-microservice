from app.auth.auth_utils import generate_token_with_role
from app.models.goal import GoalTypes, UserRoles
from dotenv import load_dotenv
load_dotenv()
import mongomock
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from app.main import app, logger
# TEST
client = TestClient(app)

athlete_id_example_mock_1 = str(ObjectId())
access_token_athlete_example_mock_1 = generate_token_with_role(athlete_id_example_mock_1, UserRoles.ATLETA)

# Mock users
goal_mock_1 = {
    "title": "Alta meta",
    "description": "La mejor meta papá",
    "metric" : GoalTypes.STEPS.value,
    "quantity_steps": 1500,
    "user_id": athlete_id_example_mock_1
}

@pytest.fixture()
def mongo_mock(monkeypatch):
    mongo_client = mongomock.MongoClient()
    db = mongo_client.get_database("goals_microservice")
    col = db.get_collection("goals")
    col.insert_one(goal_mock_1)

    app.database = db
    app.logger = logger
    monkeypatch.setattr(app, "database", db)


def test_get_goal_mocked(mongo_mock):
    response = client.get("/athletes/me/goals", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == goal_mock_1["title"]
    assert response.json()[0]["description"] == goal_mock_1["description"]