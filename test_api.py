from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def start_test_game():
    return client.post("/start", json={
        "board_size": 5,
        "queue_type": "deterministic",
        "queue_pattern": "BW",
        "next_player": "black"
    })


def test_start_game():
    response = start_test_game()
    assert response.status_code == 200
    assert response.json()["status"] == "Game started"


def test_state_after_start():
    start_test_game()
    r = client.get("/state")
    assert r.status_code == 200
    assert r.json()["next_player"] == "black"


def test_valid_move_sequence():
    start_test_game()

    r1 = client.post("/play", json={"row": 3, "col": 3, "player": "black"})
    assert r1.status_code == 200

    r2 = client.post("/play", json={"row": 4, "col": 4, "player": "white"})
    assert r2.status_code == 200

    r3 = client.get("/state")
    assert r3.json()["next_player"] == "black"


def test_pass_and_resign():
    start_test_game()

    p1 = client.post("/play_pass", json="black")
    assert p1.status_code == 200

    p2 = client.post("/play_pass", json="white")
    assert p2.status_code == 200

    s = client.get("/state")
    assert s.json()["is_over"] is True


def test_history_and_legal():
    start_test_game()

    client.post("/play", json={"row": 2, "col": 2, "player": "black"})
    client.post("/play", json={"row": 3, "col": 3, "player": "white"})

    h = client.get("/history")
    assert len(h.json()) == 2
    assert h.json()[0]["player"] == "black"

    l = client.get("/legal_moves")
    assert isinstance(l.json(), list)
    assert {"row": 2, "col": 2} not in l.json()
