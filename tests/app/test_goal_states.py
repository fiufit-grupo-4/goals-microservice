import mongomock
import pytest

from datetime import datetime, timedelta, timezone
from fastapi import Response
from app.auth.auth_utils import generate_token_with_role
from app.models.goal import GoalTypes, State, UserRoles
from app.routes.goal_states import step_to_calorie, step_to_kilometer
from bson import ObjectId
from fastapi.testclient import TestClient
from app.main import app, logger

client = TestClient(app)

athlete_id_example_mock_1 = str(ObjectId())
access_token_athlete_example_mock_1 = generate_token_with_role(athlete_id_example_mock_1, UserRoles.ATLETA)

async def mock_send_notifications(*args, **kwargs):
    response = Response()
    response.status_code = 200
    response.json = lambda: {"ok" :"ok"}
    return response

@pytest.fixture()
def mock_vars(monkeypatch):
    mongo_client = mongomock.MongoClient()
    db = mongo_client.get_database("goals_microservice")
    col = db.get_collection("goals")

    app.database = db
    app.logger = logger
    monkeypatch.setattr(app, "database", db)
    monkeypatch.setattr("app.services.services.NotificationService.send_notification_completed", mock_send_notifications)


def test_initial_state_goal_created_without_training_is_not_init(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    
def test_initial_state_goal_created_with_training_is_init(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500,
                                 "training_id" : str(ObjectId())},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    

def test_start_goal_created_then_is_setted_init_with_data_init(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    assert response.json()["date_init"] is not None
    
def test_start_goal_started_returns_error(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    assert response.json()["date_init"] is not None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    
def test_start_goal_inexistent_returns_error(mock_vars):
    goal_id_inexistent = str(ObjectId())
    response = client.patch(f"/athletes/me/goals/{goal_id_inexistent}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 404
    assert response.json() == f"Goal {goal_id_inexistent} not found"
    
    
def test_starting_goal_with_limit_time_expired_returns_ok_but_goal_is_set_to_expired(mock_vars):
    database = app.database.get_collection("goals")
    goal_id = database.insert_one({"title": "Test Goal Steps", 
                                   "description": "This is a test of Goal Step", 
                                   "metric": GoalTypes.STEPS.value, 
                                   "progress_steps": 1371,
                                   "quantity_steps": 1500, 
                                   "date_init": datetime.now(timezone.utc) - timedelta(days=2), 
                                   "limit" : datetime.now(timezone.utc) - timedelta(days=1),
                                   "user_id" : athlete_id_example_mock_1,
                                   "state": State.INIT.value}).inserted_id

    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.EXPIRED.value


def test_stop_goal_not_init_returns_error(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/stop", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    assert response.json() == f"Goal {str(goal_id)} not started"
    
def test_stop_goal_started_then_is_setted_stop(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    assert response.json()["date_init"] is not None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/stop", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.STOP.value
    

def test_stop_goal_stopped_returns_error(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    goal_id = response.json()["id"]
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["date_init"] is None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    assert response.json()["date_init"] is not None
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/stop", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.STOP.value

    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/stop", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    
    
def test_stop_goal_completed_returns_error(mock_vars):
    database = app.database.get_collection("goals")
    goal_id = database.insert_one({"title": "Test Goal Steps", 
                                   "description": "This is a test of Goal Step", 
                                   "metric": GoalTypes.STEPS.value, 
                                   "progress_steps": 1502,
                                   "quantity_steps": 1500, 
                                   "limit" : None,
                                   "date_init": datetime.now(timezone.utc) - timedelta(days=2), 
                                   "date_complete": datetime.now(timezone.utc) - timedelta(days=1), 
                                   "user_id" : athlete_id_example_mock_1,
                                   "state": State.COMPLETE.value}).inserted_id

    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.COMPLETE.value    
    
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/stop", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 400
    assert response.json() == f"Goal {str(goal_id)} already completed"
    
def test_progress_steps_always_increase_steps_without_goals(mock_vars):
    response = client.get(f"/athletes/me/goals/", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json() == []
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1500}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["message"] == "All goals have been successfully updated"
    
def test_progress_steps_with_limit_time_of_goals_expired_returns_ok_but_goals_is_set_to_expired(mock_vars):
    database = app.database.get_collection("goals")
    goal_id = database.insert_one({"title": "Test Goal Steps", 
                                   "description": "This is a test of Goal Step", 
                                   "metric": GoalTypes.STEPS.value, 
                                   "progress_steps": 1371,
                                   "quantity_steps": 1500, 
                                   "date_init": datetime.now(timezone.utc) - timedelta(days=2), 
                                   "limit" : datetime.now(timezone.utc) - timedelta(days=1),
                                   "user_id" : athlete_id_example_mock_1,
                                   "state": State.INIT.value}).inserted_id

    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.INIT.value
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1500}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    assert response.json()["state"] == State.EXPIRED.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 1371
    
    
def test_progress_steps_with_goals_stopped_return_ok_but_goals_is_not_changed(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/stop", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.STOP.value
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1500}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.STOP.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 0
    
def test_progress_steps_with_goals_not_init_return_ok_but_goals_is_not_changed(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.NOT_INIT.value
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1500}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.NOT_INIT.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 0
    
    
def test_progress_steps_with_goals_metric_steps_is_increased(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 0
    
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1210}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 1210
    
    
def test_progress_steps_with_goals_metric_kilometers_is_increased(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Kilometers",
                                 "description": "This is a test of Goal Kilometers",
                                 "metric": GoalTypes.KILOMETERS.value,
                                 "quantity_steps": 2},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 2
    assert response.json()["progress_steps"] == 0
    
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1210}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 2
    assert response.json()["progress_steps"] == step_to_kilometer(1210)
    
    
def test_progress_steps_with_goals_metric_calories_is_increased(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Calories",
                                 "description": "This is a test of Goal Calories",
                                 "metric": GoalTypes.CALORIES.value,
                                 "quantity_steps": 300},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 300
    assert response.json()["progress_steps"] == 0
    
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1210}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 300
    assert response.json()["progress_steps"] == step_to_calorie(1210)
    

def test_progress_steps_with_goals_metric_steps_is_increased_and_completed(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 0
    
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1502}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.COMPLETE.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 1502
    


def test_progress_steps_with_goals_completed_is_not_increased(mock_vars):
    response = client.post("/athletes/me/goals/", 
                           json={"title": "Test Goal Steps",
                                 "description": "This is a test of Goal Step",
                                 "metric": GoalTypes.STEPS.value,
                                 "quantity_steps": 1500},
                           headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    goal_id = response.json()["id"]
    response = client.patch(f"/athletes/me/goals/{str(goal_id)}/start", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.INIT.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 0
    
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1502}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.COMPLETE.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 1502
    
    response = client.patch(f"/athletes/me/goals/progress_steps", json={"progress_steps": 1502}, headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    assert response.status_code == 200
    
    response = client.get(f"/athletes/me/goals/{str(goal_id)}", headers={"Authorization": f"Bearer {access_token_athlete_example_mock_1}"})
    logger.info(response.json())
    assert response.json()["state"] == State.COMPLETE.value
    assert response.json()["quantity_steps"] == 1500
    assert response.json()["progress_steps"] == 1502
    