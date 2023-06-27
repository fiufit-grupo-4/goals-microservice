from datetime import datetime, timedelta, timezone
from app.auth.auth_utils import generate_token_with_role
from app.models.goal import GoalTypes, State, UserRoles
from dotenv import load_dotenv

import dateutil.parser as parser
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

@pytest.fixture()
def mongo_mock(monkeypatch):
    mongo_client = mongomock.MongoClient()
    db = mongo_client.get_database("goals_microservice")
    col = db.get_collection("goals")

    app.database = db
    app.logger = logger
    monkeypatch.setattr(app, "database", db)


def test_initial_state_goal_created_without_training_is_not_init(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    
def test_initial_state_goal_created_with_training_is_init(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500,
                                 "training_id" : str(ObjectId())},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    

def test_start_goal_created_then_is_setted_init_with_data_init(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{goal_id}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    assert response.json()["date_init"] is not None
    
def test_start_goal_started_returns_error(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{goal_id}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    assert response.json()["date_init"] is not None
    
    response = client.patch(f"/athletes/me/goals/{goal_id}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    
def test_start_goal_inexistent_returns_error(mongo_mock):
    goal_id_inexistent = str(ObjectId())
    response = client.patch(f"/athletes/me/goals/{goal_id_inexistent}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 404
    assert response.json() == f"Goal {goal_id_inexistent} not found"
    
    
def test_starting_goal_with_limit_time_expired_returns_ok_but_goal_is_set_to_expired(mongo_mock):
    database = app.database.get_collection("goals")
    goal_id = database.insert_one({"title": "Test Goal Steps", 
                                   "description": "This is a test of Goal Step", 
                                   "metric": GoalTypes.STEPS.value, 
                                   "progress_steps": 1371,
                                   "quantity_steps": 1500, 
                                   "date_init": datetime.now(timezone.utc) - timedelta(days=2), 
                                   "limit" : datetime.now(timezone.utc) - timedelta(days=1),
                                   "state": State.INIT.value}).inserted_id

    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.EXPIRED.value


