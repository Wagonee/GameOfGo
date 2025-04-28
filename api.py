import uuid
import logging
import datetime
import copy
from typing import Optional, List, Literal, Dict, Any, Tuple, Set

from fastapi import FastAPI, HTTPException, Body, Path, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.deterministic_queue import DeterministicQueue, MoveQueue
from core.random_queue import RandomQueue
from core.goboard import GameState, Move, Board, IllegalMoveError, GoString
from core.gotypes import Player, Point
from core.setup_mode import SetupState

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Go Game with non standart queues API",
    description="API для управления игрой Го с настраиваемыми правилами.",
    version="1.5.2"
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_games: Dict[str, Dict[str, Any]] = {}


class Position(BaseModel):
    row: int = Field(..., gt=0, description="Номер строки (начиная с 1)")
    col: int = Field(..., gt=0, description="Номер колонки (начиная с 1)")
    color: Literal['black', 'white'] = Field(..., description="Цвет камня")


class StartGameRequest(BaseModel):
    board_size: int = Field(default=9, ge=5, le=19, description="Размер доски (NxN)")
    initial_stones: Optional[List[Position]] = Field(default=[], description="Начальная расстановка камней")
    queue_type: Literal['deterministic', 'random'] = Field(default='deterministic', description="Тип очереди ходов")
    queue_pattern: Optional[str] = Field(default="BW",
                                         description="Паттерн для детерминированной очереди (e.g., 'BW', 'BBW')")
    queue_depth: Optional[int] = Field(default=20, description="Размер 'чанка' для случайной очереди")
    simultaneous_capture_rule: Literal['opponent', 'both', 'self'] = Field(default='opponent',
                                                                           description="Правило разрешения при одновременном захвате: 'opponent' (классика), 'both', 'self'")
    delayed_capture: bool = Field(default=False,
                                  description="Использовать ли отложенный захват (снятие камней в начале хода игрока)")


class StartGameResponse(BaseModel):
    game_id: str = Field(..., description="Уникальный идентификатор созданной игры")


class PlayMoveRequest(BaseModel):
    row: int = Field(..., gt=0, description="Номер строки для хода")
    col: int = Field(..., gt=0, description="Номер колонки для хода")


class GameStatusResponse(BaseModel):
    status: str = Field(..., description="Сообщение о статусе операции")


class BoardPoint(BaseModel):
    row: int
    col: int


class GameStateResponse(BaseModel):
    game_id: str
    board: List[List[Literal['empty', 'black', 'white']]]
    board_size: int
    next_player: Literal['black', 'white']
    is_over: bool
    winner: Optional[Literal['black', 'white']] = None
    last_move: Optional[BoardPoint] = None
    simultaneous_capture_rule: Literal['opponent', 'both', 'self']
    delayed_capture: bool
    current_turn_in_pattern: Optional[int] = None
    queue_type: Literal['deterministic', 'random']
    pending_opponent_captures_count: Optional[int] = Field(None,
                                                           description="Кол-во групп противника, ожидающих снятия")
    pending_self_capture_exists: Optional[bool] = Field(None,
                                                        description="Существует ли группа игрока, ожидающая снятия")


class MoveHistoryItem(BaseModel):
    player: Literal['black', 'white']
    action: Literal['play', 'pass', 'resign']
    row: Optional[int] = None
    col: Optional[int] = None
    move_number: int


def serialize_board(board: Board) -> List[List[Literal['empty', 'black', 'white']]]:
    serialized = []
    for r in range(1, board.num_rows + 1):
        row_list = []
        for c in range(1, board.num_cols + 1):
            stone = board.get(Point(r, c))
            row_list.append(stone.name.lower() if stone else "empty")
        serialized.append(row_list)
    return serialized


async def get_game_data_dependency(game_id: str = Path(..., description="ID игры")) -> Dict[str, Any]:
    if game_id not in active_games:
        logger.warning(f"Game not found: {game_id}")
        raise HTTPException(status_code=404, detail=f"Игра с ID '{game_id}' не найдена.")
    return active_games[game_id]


@app.post("/start", response_model=StartGameResponse, status_code=201, tags=["Game Management"])
async def start_new_game(req: StartGameRequest):
    game_id = str(uuid.uuid4())
    logger.info(f"Starting new game ({game_id}) with parameters: {req.dict()}")
    try:
        if req.queue_type == 'deterministic':
            if not req.queue_pattern: raise ValueError("Queue pattern is required for 'deterministic' queue type.")
            turn_queue: MoveQueue = DeterministicQueue(req.queue_pattern)
        else:
            turn_queue: MoveQueue = RandomQueue(chunk_size=req.queue_depth or 20)

        setup = SetupState(req.board_size, req.board_size)
        for pos in req.initial_stones:
            if not (1 <= pos.row <= req.board_size and 1 <= pos.col <= req.board_size):
                raise ValueError(
                    f"Initial stone at ({pos.row},{pos.col}) is outside board ({req.board_size}x{req.board_size}).")
            player_color = Player.black if pos.color == 'black' else Player.white
            setup.place_stone(player_color, Point(pos.row, pos.col))

        game_state = GameState.from_setup(setup)
        game_config = req.model_dump(exclude={'initial_stones'})

        active_games[game_id] = {
            "state": game_state, "queue": turn_queue, "config": game_config,
            "creation_time": datetime.datetime.now(datetime.timezone.utc)
        }

        first_player = turn_queue.peek_next_player()
        logger.info(f"Game {game_id} created. Config: {game_config}. First turn: {first_player.name}")
        return StartGameResponse(game_id=game_id)

    except ValueError as ve:
        logger.error(f"Validation error starting game {game_id}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error starting game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error creating game.")


@app.get("/game/{game_id}/state", response_model=GameStateResponse, tags=["Game State"])
async def get_game_state(game_id: str = Path(..., description="ID игры"),
                         game_data: Dict[str, Any] = Depends(get_game_data_dependency)):
    logger.debug(f"Requesting state for game {game_id}")
    game_state: GameState = game_data["state"]
    turn_queue: MoveQueue = game_data["queue"]
    game_config = game_data["config"]

    try:
        next_player_obj: Player = turn_queue.peek_next_player()
        next_player_str = next_player_obj.name.lower()

        last_move_point = None
        if game_state.last_move and game_state.last_move.is_play:
            last_move_point = BoardPoint(row=game_state.last_move.point.row, col=game_state.last_move.point.col)

        winner_obj = game_state.winner()
        winner_str = winner_obj.name.lower() if winner_obj else None

        current_turn_index = None
        if isinstance(turn_queue, DeterministicQueue):
            current_turn_index = turn_queue.current_index

        pending_opponent_count = len(game_state.pending_opponent_captures)
        pending_self_exists = bool(game_state.pending_self_capture)

        return GameStateResponse(
            game_id=game_id,
            board=serialize_board(game_state.board),
            board_size=game_config["board_size"],
            next_player=next_player_str,
            is_over=game_state.is_over,
            winner=winner_str,
            last_move=last_move_point,
            simultaneous_capture_rule=game_config["simultaneous_capture_rule"],
            delayed_capture=game_config["delayed_capture"],
            current_turn_in_pattern=current_turn_index,
            queue_type=game_config["queue_type"],
            pending_opponent_captures_count=pending_opponent_count,
            pending_self_capture_exists=pending_self_exists
        )
    except Exception as e:
        logger.exception(f"Error getting state for game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting game state.")


async def _process_player_action(
        game_id: str,
        game_data: Dict[str, Any],
        move: Move
):
    current_game_state: GameState = game_data["state"]
    turn_queue: MoveQueue = game_data["queue"]
    game_config = game_data["config"]
    delayed_capture_enabled = game_config["delayed_capture"]
    simultaneous_rule = game_config["simultaneous_capture_rule"]

    if current_game_state.is_over:
        logger.warning(f"Game {game_id}: Action '{move}' attempted but game is already over.")
        raise HTTPException(status_code=400, detail="Игра уже завершена.")

    player_whose_turn_it_is: Player = turn_queue.peek_next_player()
    logger.info(
        f"Game {game_id}: Turn for {player_whose_turn_it_is.name}. Received action: '{move}'. Delayed capture: {delayed_capture_enabled}")

    state_to_play_on = current_game_state

    if delayed_capture_enabled:
        logger.debug(f"Checking for delayed captures before {player_whose_turn_it_is.name}'s move.")
        pending_opponent_groups = current_game_state.pending_opponent_captures
        pending_self_capture_group = current_game_state.pending_self_capture
        groups_to_remove_now: Set[GoString] = set()

        if pending_opponent_groups or pending_self_capture_group:
            is_simultaneous = bool(pending_opponent_groups) and bool(pending_self_capture_group)
            player_color = player_whose_turn_it_is

            logger.debug(f"Checking Pending Opponent: {pending_opponent_groups}")
            logger.debug(f"Checking Pending Self: {pending_self_capture_group}")
            logger.debug(
                f"Player Turn: {player_color}, Sim: {is_simultaneous}, SimRule: {simultaneous_rule}")  # Removed CapMode

            if is_simultaneous:
                for group in pending_opponent_groups:
                    if group.color == player_color:
                        if simultaneous_rule in ('opponent', 'both'):
                            groups_to_remove_now.add(group)
                            logger.debug(
                                f"Marking Opponent group {repr(group)} for removal (Sim rule={simultaneous_rule})")
                if pending_self_capture_group and pending_self_capture_group.color == player_color:
                    if simultaneous_rule in ('self', 'both'):
                        groups_to_remove_now.add(pending_self_capture_group)
                        logger.debug(
                            f"Marking Self group {repr(pending_self_capture_group)} for removal (Sim rule={simultaneous_rule})")
            else:
                if pending_opponent_groups:
                    for group in pending_opponent_groups:
                        if group.color == player_color:
                            groups_to_remove_now.add(group)
                            logger.debug(f"Marking Opponent group {repr(group)} for removal (Opponent only)")
                elif pending_self_capture_group:
                    if pending_self_capture_group.color == player_color:
                        groups_to_remove_now.add(pending_self_capture_group)
                        logger.debug(f"Marking Self group {repr(pending_self_capture_group)} for removal (Self only)")

            if groups_to_remove_now:
                board_after_cleanup_copy = copy.deepcopy(current_game_state.board)
                logger.info(
                    f"Performing delayed removal for {player_whose_turn_it_is.name}: {[repr(g) for g in groups_to_remove_now]}")
                successfully_removed_count = 0
                for group in groups_to_remove_now:
                    representative_point = next(iter(group.stones), None)
                    if not representative_point: continue
                    string_on_copied_board = board_after_cleanup_copy.get_go_string(representative_point)

                    if string_on_copied_board and string_on_copied_board == group:
                        current_liberties = {n for p in string_on_copied_board.stones for n in p.neighbors() if
                                             board_after_cleanup_copy.is_on_grid(n) and board_after_cleanup_copy.get(
                                                 n) is None}
                        if not current_liberties:
                            logger.debug(f"Removing group {repr(string_on_copied_board)} from copied board.")
                            board_after_cleanup_copy._remove_string(string_on_copied_board)
                            successfully_removed_count += 1
                        else:
                            logger.warning(
                                f"Group {repr(string_on_copied_board)} marked for delayed removal now has {len(current_liberties)} liberties. Skipping.")
                    else:
                        logger.warning(
                            f"Group {repr(group)} not found or changed before removal. Found: {repr(string_on_copied_board)}")

                if successfully_removed_count > 0:
                    remaining_pending_opponent_set = set(pending_opponent_groups) - groups_to_remove_now
                    new_remaining_pending_self = None
                    if pending_self_capture_group and pending_self_capture_group not in groups_to_remove_now:
                        new_remaining_pending_self = pending_self_capture_group

                    state_after_cleanup = GameState(
                        board=board_after_cleanup_copy,
                        previous=current_game_state,
                        move=None,
                        move_history=current_game_state.move_history,
                        pending_opponent_captures=frozenset(remaining_pending_opponent_set),
                        pending_self_capture=new_remaining_pending_self
                    )
                    state_after_cleanup.previous_states = current_game_state.previous_states | {
                        current_game_state.board.zobrist_hash()}

                    state_to_play_on = state_after_cleanup
                    logger.debug(
                        f"Created intermediate state after cleanup. Hash: {state_after_cleanup.board.zobrist_hash()}. Remaining pending: Opponent={len(remaining_pending_opponent_set)}, Self={bool(new_remaining_pending_self)}")
                else:
                    logger.debug(
                        "Groups matching player color found for delayed capture but none actually removed (e.g., they gained liberties). Playing on original state.")
                    current_player_pending_opponent = {g for g in pending_opponent_groups if g.color == player_color}
                    current_player_pending_self = {
                        pending_self_capture_group} if pending_self_capture_group and pending_self_capture_group.color == player_color else set()

                    survived_groups = current_player_pending_opponent.union(current_player_pending_self)

                    if survived_groups:
                        remaining_pending_opponent_set = set(pending_opponent_groups) - survived_groups
                        new_remaining_pending_self = None
                        if pending_self_capture_group and pending_self_capture_group not in survived_groups:
                            new_remaining_pending_self = pending_self_capture_group

                        state_with_cleared_pending = GameState(
                            board=current_game_state.board,
                            previous=current_game_state.previous_state,
                            move=current_game_state.last_move,
                            move_history=current_game_state.move_history,
                            pending_opponent_captures=frozenset(remaining_pending_opponent_set),
                            pending_self_capture=new_remaining_pending_self
                        )
                        state_with_cleared_pending.previous_states = current_game_state.previous_states
                        state_to_play_on = state_with_cleared_pending
                        logger.debug(
                            f"Cleared pending captures for surviving groups. State hash {state_to_play_on.board.zobrist_hash()}. Pending: Opponent={len(state_to_play_on.pending_opponent_captures)}, Self={bool(state_to_play_on.pending_self_capture)}")

    try:
        if not state_to_play_on.is_valid_move(player_whose_turn_it_is, move):
            logger.warning(
                f"Invalid action {move} for player {player_whose_turn_it_is.name} (checked on state hash {state_to_play_on.board.zobrist_hash()}).")
            raise IllegalMoveError(f"Недопустимый ход: {move}")

        final_state = state_to_play_on.apply_move(
            player_making_move=player_whose_turn_it_is,
            move=move,
            simultaneous_capture_rule=simultaneous_rule,
            delayed_capture=delayed_capture_enabled
        )
        action_type = "played stone" if move.is_play else "passed" if move.is_pass else "resigned"

        active_games[game_id]["state"] = final_state
        logger.info(
            f"Game {game_id}: Player {player_whose_turn_it_is.name} {action_type} successful. Final state hash: {final_state.board.zobrist_hash()}. Final Pending: Opponent={len(final_state.pending_opponent_captures)}, Self={bool(final_state.pending_self_capture)}")

        turn_queue.advance_turn()
        next_player_in_queue = turn_queue.peek_next_player()
        logger.debug(f"Game {game_id}: Turn queue advanced. Next player in queue: {next_player_in_queue.name}")

        return {"status": f"Действие '{move}' игрока {player_whose_turn_it_is.name.lower()} успешно принято."}

    except IllegalMoveError as illegal_move:
        logger.warning(
            f"Game {game_id}: Illegal move error processing action {move} for {player_whose_turn_it_is.name}: {illegal_move}")
        raise HTTPException(status_code=400, detail=f"Недопустимый ход: {illegal_move}")
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.exception(
            f"Game {game_id}: Internal server error processing action {move} for {player_whose_turn_it_is.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке действия: {e}")


@app.post("/game/{game_id}/play", response_model=GameStatusResponse, tags=["Game Actions"])
async def play_stone(req: PlayMoveRequest, game_id: str = Path(..., description="ID игры"),
                     game_data: Dict[str, Any] = Depends(get_game_data_dependency)):
    board_size = game_data["config"]["board_size"]
    if not (1 <= req.row <= board_size and 1 <= req.col <= board_size):
        raise HTTPException(status_code=400,
                            detail=f"Координаты хода ({req.row},{req.col}) вне доски {board_size}x{board_size}.")
    point = Point(req.row, req.col)
    move = Move.play(point)
    return await _process_player_action(game_id, game_data, move)


@app.post("/game/{game_id}/pass", response_model=GameStatusResponse, tags=["Game Actions"])
async def play_pass_turn(game_id: str = Path(..., description="ID игры"),
                         game_data: Dict[str, Any] = Depends(get_game_data_dependency)):
    move = Move.pass_turn()
    return await _process_player_action(game_id, game_data, move)


@app.post("/game/{game_id}/resign", response_model=GameStatusResponse, tags=["Game Actions"])
async def play_resign_game(game_id: str = Path(..., description="ID игры"),
                           game_data: Dict[str, Any] = Depends(get_game_data_dependency)):
    move = Move.resign()
    return await _process_player_action(game_id, game_data, move)


@app.get("/game/{game_id}/legal_moves", response_model=List[BoardPoint], tags=["Game Info"])
async def get_legal_moves(
        game_id: str = Path(..., description="ID игры"),
        game_data: Dict[str, Any] = Depends(get_game_data_dependency)
):
    game_state: GameState = game_data["state"]
    turn_queue: MoveQueue = game_data["queue"]
    game_config = game_data["config"]
    delayed_capture_enabled = game_config["delayed_capture"]
    simultaneous_rule = game_config["simultaneous_capture_rule"]

    if game_state.is_over:
        return []

    try:
        player_to_move = turn_queue.peek_next_player()
        state_for_legal_moves = game_state

        if delayed_capture_enabled:
            logger.debug(f"Simulating delayed capture cleanup for legal moves check (player: {player_to_move.name})")
            pending_opponent_groups = game_state.pending_opponent_captures
            pending_self_capture_group = game_state.pending_self_capture
            groups_to_remove_now: Set[GoString] = set()

            if pending_opponent_groups or pending_self_capture_group:
                is_simultaneous = bool(pending_opponent_groups) and bool(pending_self_capture_group)
                player_color = player_to_move

                logger.debug(f"Sim Pending Opponent: {pending_opponent_groups}")
                logger.debug(f"Sim Pending Self: {pending_self_capture_group}")
                logger.debug(f"Sim Player Turn: {player_color}, Sim: {is_simultaneous}, SimRule: {simultaneous_rule}")

                if is_simultaneous:
                    for group in pending_opponent_groups:
                        if group.color == player_color:
                            if simultaneous_rule in ('opponent', 'both'):
                                groups_to_remove_now.add(group)
                    if pending_self_capture_group and pending_self_capture_group.color == player_color:
                        if simultaneous_rule in ('self', 'both'):
                            groups_to_remove_now.add(pending_self_capture_group)
                else:
                    if pending_opponent_groups:
                        for group in pending_opponent_groups:
                            if group.color == player_color:
                                groups_to_remove_now.add(group)
                    elif pending_self_capture_group:
                        if pending_self_capture_group.color == player_color:
                            groups_to_remove_now.add(pending_self_capture_group)

                if groups_to_remove_now:
                    temp_board = copy.deepcopy(game_state.board)
                    removed_count = 0
                    logger.debug(f"Simulating removal of: {[repr(g) for g in groups_to_remove_now]}")
                    for group in groups_to_remove_now:
                        rep_point = next(iter(group.stones), None)
                        if not rep_point: continue
                        string_on_temp = temp_board.get_go_string(rep_point)
                        if string_on_temp and string_on_temp == group:
                            libs = {n for p in string_on_temp.stones for n in p.neighbors() if
                                    temp_board.is_on_grid(n) and temp_board.get(n) is None}
                            if not libs:
                                temp_board._remove_string(string_on_temp)
                                removed_count += 1
                            else:
                                logger.debug(f"Sim: Group {repr(string_on_temp)} survived, has {len(libs)} liberties.")
                        else:
                            logger.debug(f"Sim: Group {repr(group)} not found or changed.")

                    if removed_count > 0:
                        remaining_pending_opp_set = set(pending_opponent_groups) - groups_to_remove_now
                        new_remaining_pending_self = None
                        if pending_self_capture_group and pending_self_capture_group not in groups_to_remove_now:
                            new_remaining_pending_self = pending_self_capture_group

                        state_after_sim_cleanup = GameState(
                            board=temp_board,
                            previous=game_state,
                            move=None,
                            move_history=game_state.move_history,
                            pending_opponent_captures=frozenset(remaining_pending_opp_set),
                            pending_self_capture=new_remaining_pending_self
                        )
                        state_after_sim_cleanup.previous_states = game_state.previous_states | {
                            game_state.board.zobrist_hash()}
                        state_for_legal_moves = state_after_sim_cleanup
                        logger.debug(
                            f"Using simulated state after cleanup for legal moves. Hash: {state_after_sim_cleanup.board.zobrist_hash()}")
                    else:
                        logger.debug(
                            "Simulated cleanup resulted in no removals. Using original state but clearing relevant pending captures.")
                        current_player_pending_opponent = {g for g in pending_opponent_groups if
                                                           g.color == player_color}
                        current_player_pending_self = {
                            pending_self_capture_group} if pending_self_capture_group and pending_self_capture_group.color == player_color else set()
                        survived_groups = current_player_pending_opponent.union(current_player_pending_self)

                        if survived_groups:
                            remaining_pending_opponent_set = set(pending_opponent_groups) - survived_groups
                            new_remaining_pending_self = None
                            if pending_self_capture_group and pending_self_capture_group not in survived_groups:
                                new_remaining_pending_self = pending_self_capture_group

                            state_with_cleared_pending = GameState(
                                board=game_state.board,  # Same board
                                previous=game_state.previous_state,
                                move=game_state.last_move,
                                move_history=game_state.move_history,
                                pending_opponent_captures=frozenset(remaining_pending_opponent_set),
                                pending_self_capture=new_remaining_pending_self
                            )
                            state_with_cleared_pending.previous_states = game_state.previous_states
                            state_for_legal_moves = state_with_cleared_pending
                            logger.debug(
                                f"Using state with cleared pending captures. Hash {state_for_legal_moves.board.zobrist_hash()}. Pending: Opponent={len(state_for_legal_moves.pending_opponent_captures)}, Self={bool(state_for_legal_moves.pending_self_capture)}")

        all_legal_actions = state_for_legal_moves.legal_moves(player_to_move)

        legal_placements = [
            BoardPoint(row=move.point.row, col=move.point.col)
            for move in all_legal_actions
            if move.is_play
        ]
        logger.debug(f"Found {len(legal_placements)} legal placement moves for {player_to_move.name}.")
        return legal_placements
    except Exception as e:
        logger.exception(f"Error getting legal moves for game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting legal moves.")


@app.get("/game/{game_id}/history", response_model=List[MoveHistoryItem], tags=["Game Info"])
async def get_game_history(game_id: str = Path(..., description="ID игры"),
                           game_data: Dict[str, Any] = Depends(get_game_data_dependency)):
    game_state: GameState = game_data["state"]
    try:
        history = []
        for i, (move, player) in enumerate(game_state.move_history):
            item = MoveHistoryItem(player=player.name.lower(), action="play", move_number=i + 1)
            if move.is_play:
                item.row = move.point.row
                item.col = move.point.col
            elif move.is_pass:
                item.action = "pass"
            elif move.is_resign:
                item.action = "resign"
            history.append(item)
        return history
    except Exception as e:
        logger.exception(f"Error getting history for game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting game history.")


@app.delete("/game/{game_id}", status_code=204, tags=["Game Management"])
async def delete_game(game_id: str = Path(..., description="ID игры для удаления")):
    logger.info(f"Request to delete game {game_id}")
    if game_id in active_games:
        del active_games[game_id]
        logger.info(f"Game {game_id} deleted successfully.")
        return Response(status_code=204)
    else:
        logger.warning(f"Attempted to delete non-existent game: {game_id}")
        raise HTTPException(status_code=404, detail=f"Игра с ID '{game_id}' не найдена.")


@app.get("/", tags=["Root"], include_in_schema=False)
async def read_root():
    return {"message": "Welcome to the Go Game API! See /docs for details."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
