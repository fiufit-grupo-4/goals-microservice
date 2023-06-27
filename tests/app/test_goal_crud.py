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
    
def test_post_goal(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["description"] == "This is a test of Goal Step"
    
    response = client.get("/athletes/me/goals", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[1]["description"] == "This is a test of Goal Step"
    assert response.json()[1]["state"] == State.NOT_INIT.value
    
def test_post_goal_limit_time_invalid(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500,
                                 "limit_time": "2021-06-01"},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 422
    
def test_post_goal_limit_time_greater_than_current_date(mongo_mock):
    limit = str((datetime.now(timezone.utc) + timedelta(minutes=1)))
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1,
                                 "limit_time": limit},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert parser.parse(response.json()["limit_time"]).replace(tzinfo=timezone.utc) == parser.parse(limit).replace(tzinfo=timezone.utc)
    
def test_post_goal_limit_time_less_than_current_date_is_ok(mongo_mock):
    limit = str((datetime.now(timezone.utc) - timedelta(minutes=1)))
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1,
                                 "limit_time": limit},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    assert response.json()["message"] == "Limit date is before current date"
    
def test_post_goal_with_training_starts_the_goal(mongo_mock):
    training_id = str(ObjectId())
    response = client.post("/athletes/me/goals/",
                           json={"title": "Test Goal Steps of Training",
                                 "description": "This is a test of Goal Step of Training",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1,
                                 "training_id": training_id},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["description"] == "This is a test of Goal Step of Training"
    
    response = client.get("/athletes/me/goals", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[1]["description"] == "This is a test of Goal Step of Training"
    assert response.json()[1]["state"] == State.INIT.value
    assert response.json()[1]["training_id"] is not None
    assert response.json()[1]["date_init"] is not None
    
def test_get_especific_goal(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["description"] == "This is a test of Goal Step"
    

def test_get_especific_goal_inexistent(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    
    response = client.get(f"/athletes/me/goals/{athlete_id_example_mock_1}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 404
    assert response.json() == f"Goal {athlete_id_example_mock_1} not found to get"
    
def test_delete_goal(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]

    response = client.get("/athletes/me/goals", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    response = client.delete("/athletes/me/goals/" + goal_id, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200

    response = client.get("/athletes/me/goals", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    
def test_delete_goal_inexistent(mongo_mock):
    response = client.delete("/athletes/me/goals/" + athlete_id_example_mock_1, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 404
    assert response.json() == f"Goal {athlete_id_example_mock_1} not found to delete"
    
    
def test_patch_goal(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]

    response = client.patch(f"/athletes/me/goals/{goal_id}",
                            json={"title": "Test Goal Steps Patched!",
                                  "description" : "Nice patch"}, 
                            headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200

    response = client.get("/athletes/me/goals", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[1]["title"] == "Test Goal Steps Patched!"
    assert response.json()[1]["description"] == "Nice patch"
    
def test_patch_goal_ineeexistent(mongo_mock):
    response = client.patch(f"/athletes/me/goals/{athlete_id_example_mock_1}",
                            json={"title": "Test Goal Steps Patched!",
                                  "description" : "Nice patch"}, 
                            headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 404
    assert response.json() == f"Goal {athlete_id_example_mock_1} not found to update"
    
def test_patch_goal_without_changes_return_bad_request(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]

    response = client.patch(f"/athletes/me/goals/{goal_id}",
                            json = {},
                            headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    assert response.json() == "No values specified to update"
        
    response = client.patch(f"/athletes/me/goals/{goal_id}",
                            json = {"title": None},
                            headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    assert response.json() == "No values specified to update"
    
def test_patch_goal_with_limit_time_less_than_current_date(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    
    limit_time = str((datetime.now(timezone.utc) - timedelta(minutes=1)))
    response = client.patch(f"/athletes/me/goals/{goal_id}", 
                           json={"limit_time": limit_time},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    
    assert response.status_code == 400
    assert response.json()["message"] == "Limit date is before current date"
    
def test_patch_goal_expired_then_resets_the_goal(mongo_mock):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500,
                                 "state" : State.EXPIRED.value},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.EXPIRED.value
    
    response = client.patch(f"/athletes/me/goals/{goal_id}", 
                           json={"limit_time": str(datetime.now(timezone.utc) + timedelta(days=1))},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{goal_id}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    