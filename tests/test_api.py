import pytest
from fastapi.testclient import TestClient
import uuid

from api import app, active_games
from core.gotypes import Point


@pytest.fixture(scope="function")
def client():
    active_games.clear()
    with TestClient(app) as c:
        yield c
    active_games.clear()


def test_start_game_default(client):
    response = client.post("/start", json={})  # Use default params
    assert response.status_code == 201
    data = response.json()
    assert "game_id" in data
    game_id = data["game_id"]
    assert game_id in active_games
    assert active_games[game_id]["config"]["board_size"] == 9
    assert active_games[game_id]["config"]["queue_type"] == "deterministic"
    assert active_games[game_id]["config"]["queue_pattern"] == "BW"
    assert active_games[game_id]["config"]["delayed_capture"] == False
    assert active_games[game_id]["config"]["simultaneous_capture_rule"] == "opponent"


def test_start_game_custom_size(client):
    response = client.post("/start", json={"board_size": 13})
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    assert active_games[game_id]["config"]["board_size"] == 13


def test_start_game_invalid_size_too_small(client):
    response = client.post("/start", json={"board_size": 4})
    assert response.status_code == 422


def test_start_game_invalid_size_too_large(client):
    response = client.post("/start", json={"board_size": 20})
    assert response.status_code == 422


def test_start_game_deterministic_queue(client):
    pattern = "BBW"
    response = client.post("/start", json={
        "queue_type": "deterministic",
        "queue_pattern": pattern
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    assert active_games[game_id]["config"]["queue_type"] == "deterministic"
    assert active_games[game_id]["config"]["queue_pattern"] == pattern
    from core.deterministic_queue import DeterministicQueue
    assert isinstance(active_games[game_id]["queue"], DeterministicQueue)


def test_start_game_random_queue(client):
    depth = 15
    response = client.post("/start", json={
        "queue_type": "random",
        "queue_depth": depth
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    assert active_games[game_id]["config"]["queue_type"] == "random"
    assert active_games[game_id]["config"]["queue_depth"] == depth
    from core.random_queue import RandomQueue
    assert isinstance(active_games[game_id]["queue"], RandomQueue)


def test_start_game_initial_stones(client):
    stones = [
        {"row": 3, "col": 3, "color": "black"},
        {"row": 4, "col": 4, "color": "white"},
    ]
    response = client.post("/start", json={
        "board_size": 5,
        "initial_stones": stones
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    state = active_games[game_id]["state"]
    assert state.board.get(Point(3, 3)).name == "black"
    assert state.board.get(Point(4, 4)).name == "white"
    assert state.board.get(Point(1, 1)) is None


def test_start_game_initial_stones_invalid_coords(client):
    stones = [{"row": 6, "col": 3, "color": "black"}]
    response = client.post("/start", json={"board_size": 5, "initial_stones": stones})
    assert response.status_code == 400


def test_start_game_custom_rules(client):
    response = client.post("/start", json={
        "delayed_capture": True,
        "simultaneous_capture_rule": "both"
    })
    assert response.status_code == 201
    game_id = response.json()["game_id"]
    assert active_games[game_id]["config"]["delayed_capture"] == True
    assert active_games[game_id]["config"]["simultaneous_capture_rule"] == "both"


def test_delete_game(client):
    start_response = client.post("/start", json={})
    game_id = start_response.json()["game_id"]
    assert game_id in active_games

    delete_response = client.delete(f"/game/{game_id}")
    assert delete_response.status_code == 204
    assert game_id not in active_games


def test_delete_game_not_found(client):
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/game/{fake_id}")
    assert response.status_code == 404


@pytest.fixture
def started_game(client):
    response = client.post("/start", json={"board_size": 5})
    assert response.status_code == 201
    return response.json()["game_id"]


def test_get_game_state_ok(client, started_game):
    response = client.get(f"/game/{started_game}/state")
    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == started_game
    assert data["board_size"] == 5
    assert data["next_player"] == "black"
    assert not data["is_over"]
    assert data["winner"] is None
    assert isinstance(data["board"], list)
    assert len(data["board"]) == 5
    assert len(data["board"][0]) == 5
    assert data["board"][0][0] == "empty"
    assert data["delayed_capture"] == False
    assert data["simultaneous_capture_rule"] == "opponent"
    assert data["queue_type"] == "deterministic"


def test_get_game_state_404(client):
    fake_id = str(uuid.uuid4())
    response = client.get(f"/game/{fake_id}/state")
    assert response.status_code == 404


def test_get_legal_moves_start(client, started_game):
    response = client.get(f"/game/{started_game}/legal_moves")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 25
    assert {"row": 1, "col": 1} in data
    assert {"row": 3, "col": 3} in data
    assert {"row": 5, "col": 5} in data


def test_get_history_empty(client, started_game):
    response = client.get(f"/game/{started_game}/history")
    assert response.status_code == 200
    assert response.json() == []


def test_play_stone_ok(client, started_game):
    move_data = {"row": 3, "col": 3}
    response = client.post(f"/game/{started_game}/play", json=move_data)
    assert response.status_code == 200
    assert "status" in response.json()
    assert "black" in response.json()["status"].lower()

    # Verify board state
    state_response = client.get(f"/game/{started_game}/state")
    board = state_response.json()["board"]
    assert board[2][2] == "black"
    assert state_response.json()["next_player"] == "white"  # BW queue


def test_play_stone_off_board(client, started_game):
    move_data = {"row": 6, "col": 3}
    response = client.post(f"/game/{started_game}/play", json=move_data)
    assert response.status_code == 400


def test_play_stone_occupied(client, started_game):
    client.post(f"/game/{started_game}/play", json={"row": 3, "col": 3})
    response = client.post(f"/game/{started_game}/play", json={"row": 3, "col": 3})
    assert response.status_code == 400
    assert "Недопустимый ход" in response.json()["detail"]


def test_pass_turn_ok(client, started_game):
    response = client.post(f"/game/{started_game}/pass")
    assert response.status_code == 200
    assert "pass" in response.json()["status"].lower()
    assert "black" in response.json()["status"].lower()

    state_response = client.get(f"/game/{started_game}/state")
    assert state_response.json()["next_player"] == "white"


def test_resign_game_ok(client, started_game):
    response = client.post(f"/game/{started_game}/resign")
    assert response.status_code == 200
    assert "resign" in response.json()["status"].lower()
    assert "black" in response.json()["status"].lower()

    state_response = client.get(f"/game/{started_game}/state")
    assert state_response.json()["is_over"] == True
    assert state_response.json()["winner"] == "white"


def test_play_after_game_over(client, started_game):
    client.post(f"/game/{started_game}/resign")
    response = client.post(f"/game/{started_game}/play", json={"row": 1, "col": 1})
    assert response.status_code == 400
    assert "Игра уже завершена" in response.json()["detail"]


def test_get_history_after_moves(client, started_game):
    client.post(f"/game/{started_game}/play", json={"row": 3, "col": 3})  # Black
    client.post(f"/game/{started_game}/pass")
    client.post(f"/game/{started_game}/play", json={"row": 1, "col": 1})  # Black

    response = client.get(f"/game/{started_game}/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 3
    assert history[0]["player"] == "black"
    assert history[0]["action"] == "play"
    assert history[0]["row"] == 3
    assert history[0]["col"] == 3
    assert history[0]["move_number"] == 1
    assert history[1]["player"] == "white"
    assert history[1]["action"] == "pass"
    assert history[1]["move_number"] == 2
    assert history[2]["player"] == "black"
    assert history[2]["action"] == "play"
    assert history[2]["row"] == 1
    assert history[2]["col"] == 1
    assert history[2]["move_number"] == 3
