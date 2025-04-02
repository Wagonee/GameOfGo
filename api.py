from typing import Optional, List, Literal

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel

import dlgo.game_config as game_config
from dlgo.deterministic_queue import DeterministicQueue
from dlgo.goboard import GameState, Move
from dlgo.gotypes import Player, Point
from dlgo.random_queue import RandomQueue
from dlgo.setup_mode import SetupState

app = FastAPI()


class Position(BaseModel):
    row: int
    col: int
    color: Literal['black', 'white']


class StartGameRequest(BaseModel):
    board_size: int = 9
    initial_stones: Optional[List[Position]] = []
    queue_type: Optional[Literal['deterministic', 'random']] = 'deterministic'
    queue_pattern: Optional[str] = "BW"
    queue_depth: Optional[int] = 20
    capture_mode: Optional[Literal['both', 'white_only', 'black_only']] = 'both'
    delayed_capture: Optional[bool] = True
    next_player: Literal['black', 'white'] = 'black'


class PlayMoveRequest(BaseModel):
    row: int
    col: int
    player: Literal['black', 'white']  # "black" или "white"


game: Optional[GameState] = None
turn_queue = None


def serialize_board(board):
    return [
        [
            board.get(Point(row, col)).name.lower() if board.get(Point(row, col)) else "empty"
            for col in range(1, board.num_cols + 1)
        ]
        for row in range(1, board.num_rows + 1)
    ]


def get_player(player_str: Literal['black', 'white']) -> Player:
    return Player.black if player_str == 'black' else Player.white


@app.post("/start")
def start_game(req: StartGameRequest):
    global game, turn_queue

    # Установка параметров захвата
    game_config.capture_mode = req.capture_mode
    game_config.delayed_capture = req.delayed_capture

    # Установка камней перед началом игры
    setup = SetupState(req.board_size, req.board_size)
    for pos in req.initial_stones:
        setup.place_stone(get_player(pos.color), Point(pos.row, pos.col))

    game = GameState.from_setup(setup, get_player(req.next_player))

    if req.queue_type == 'deterministic':
        turn_queue = DeterministicQueue(req.queue_pattern)
    else:
        turn_queue = RandomQueue(req.queue_depth)

    return {"status": "Game started"}


@app.get("/state")
def get_state():
    if game is None:
        raise HTTPException(status_code=400, detail="Game not started")

    if turn_queue is not None:
        next_player = turn_queue.next_player().name.lower()
    else:
        next_player = game.next_player.name.lower()

    state = {
        "board": serialize_board(game.board),
        "next_player": next_player,
        "is_over": game.is_over,
        "winner": game.winner().name.lower() if game.winner() else None,
        "last_move": {
            "row": game.last_move.point.row,
            "col": game.last_move.point.col
        } if game.last_move and game.last_move.point else None
    }
    return state


@app.post("/play")
def play_move(req: PlayMoveRequest):
    global game
    if game is None:
        raise HTTPException(status_code=400, detail="Game not started")

    try:
        point = Point(req.row, req.col)
        move = Move.play(point)
        player = get_player(req.player)

        expected_player = turn_queue.next_player() if turn_queue else game.next_player

        if player != expected_player:
            raise HTTPException(status_code=400, detail=f"It's {expected_player.name.lower()}'s turn")

        if not game.is_valid_move(move):
            raise HTTPException(status_code=400, detail="Invalid move")

        game = game.apply_move(move)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "Move played"}


@app.get("/legal_moves")
def get_legal_moves():
    if game is None:
        raise HTTPException(status_code=400, detail="Game not started")

    legal = [
        {"row": move.point.row, "col": move.point.col}
        for move in game.legal_moves()
        if move.is_play
    ]
    return legal


@app.get("/history")
def get_history():
    if game is None:
        raise HTTPException(status_code=400, detail="Game not started")

    moves = []
    for move, player in game.move_history:
        if move.is_play:
            moves.append({
                "player": player.name.lower(),
                "row": move.point.row,
                "col": move.point.col
            })
        elif move.is_pass:
            moves.append({
                "player": player.name.lower(),
                "action": "pass"
            })
        elif move.is_resign:
            moves.append({
                "player": player.name.lower(),
                "action": "resign"
            })
    return moves


@app.post("/play_pass")
def play_pass(player: Literal["black", "white"] = Body(...)):
    global game
    if game is None:
        raise HTTPException(status_code=400, detail="Game not started")

    p = get_player(player)
    expected_player = turn_queue.next_player() if turn_queue else game.next_player

    if p != expected_player:
        raise HTTPException(status_code=400, detail=f"It's {expected_player.name.lower()}'s turn")

    move = Move.pass_turn()
    if not game.is_valid_move(move):
        raise HTTPException(status_code=400, detail="Invalid pass")

    game = game.apply_move(move)
    return {"status": "Pass played"}


@app.post("/play_resign")
def play_resign(player: Literal["black", "white"] = Body(...)):
    global game
    if game is None:
        raise HTTPException(status_code=400, detail="Game not started")

    p = get_player(player)
    expected_player = turn_queue.next_player() if turn_queue else game.next_player

    if p != expected_player:
        raise HTTPException(status_code=400, detail=f"It's {expected_player.name.lower()}'s turn")

    move = Move.resign()
    game = game.apply_move(move)
    return {"status": "Player resigned"}


@app.post("/reset")
def reset_game():
    global game, turn_queue
    game = None
    turn_queue = None
    return {"status": "Game reset"}
