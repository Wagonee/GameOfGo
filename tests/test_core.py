import pytest
import copy
from core.goboard import Board, GameState, Move, GoString, IllegalMoveError
from core.gotypes import Player, Point
from core.deterministic_queue import DeterministicQueue
from core.random_queue import RandomQueue
from core.setup_mode import SetupState
from core.scoring import compute_game_result, evaluate_territory
from core.agent.helpers import is_point_an_eye

def test_board_init():
    board = Board(9, 9)
    assert board.num_rows == 9
    assert board.num_cols == 9
    assert len(board._grid) == 0

def test_board_place_stone():
    board = Board(5, 5)
    point = Point(3, 3)
    board.place_stone(Player.black, point)
    assert board.get(point) == Player.black
    assert board._grid[point].color == Player.black
    assert len(board._grid) == 1

def test_board_place_stone_occupied():
    board = Board(5, 5)
    point = Point(3, 3)
    board.place_stone(Player.black, point)
    with pytest.raises(IllegalMoveError):
        board.place_stone(Player.white, point)

def test_board_is_on_grid():
    board = Board(5, 5)
    assert board.is_on_grid(Point(1, 1))
    assert board.is_on_grid(Point(5, 5))
    assert not board.is_on_grid(Point(0, 1))
    assert not board.is_on_grid(Point(6, 5))
    assert not board.is_on_grid(Point(1, 0))
    assert not board.is_on_grid(Point(5, 6))

def test_board_simple_capture():
    board = Board(5, 5)
    # . . . . .
    # . . B . .
    # . B W B .
    # . . B . .
    # . . . . .
    board.place_stone(Player.black, Point(2, 3))
    board.place_stone(Player.black, Point(3, 2))
    board.place_stone(Player.black, Point(4, 3))
    board.place_stone(Player.white, Point(3, 3))
    # Capture move
    board.place_stone(Player.black, Point(3, 4))
    assert board.get(Point(3, 3)) is None
    assert board.get(Point(2, 3)) == Player.black

def test_board_string_merge():
    board = Board(5, 5)
    # . . .
    # B B .
    # . . .
    p1 = Point(2, 1)
    p2 = Point(2, 2)
    p3 = Point(2, 3)
    board.place_stone(Player.black, p1)
    board.place_stone(Player.black, p2)
    string1 = board.get_go_string(p1)
    string2 = board.get_go_string(p2)
    board.place_stone(Player.black, p3)
    string_final = board.get_go_string(p1)
    assert string_final is not None, "String should exist at p1"
    string_at_p2 = board.get_go_string(p2)
    string_at_p3 = board.get_go_string(p3)
    assert string_at_p2 is not None, "String should exist at p2"
    assert string_at_p3 is not None, "String should exist at p3"
    assert string_final == string_at_p2
    assert string_final == string_at_p3
    assert len(string_final.stones) == 3

def test_gamestate_new_game():
    setup = SetupState(9, 9)
    gs = GameState.from_setup(setup)
    assert gs.board.num_rows == 9
    assert gs.board.num_cols == 9
    assert gs.previous_state is None
    assert gs.last_move is None
    assert len(gs.move_history) == 0

def test_gamestate_from_setup():
    setup = SetupState(5, 5)
    p_b = Point(3, 3)
    p_w = Point(3, 4)
    setup.place_stone(Player.black, p_b)
    setup.place_stone(Player.white, p_w)
    gs = GameState.from_setup(setup)
    assert gs.board.get(p_b) == Player.black
    assert gs.board.get(p_w) == Player.white
    assert gs.board.get(Point(1,1)) is None

@pytest.fixture
def basic_game():
    setup = SetupState(5, 5)
    return GameState.from_setup(setup)

def test_gamestate_apply_play(basic_game):
    move = Move.play(Point(3, 3))
    next_state = basic_game.apply_move(Player.black, move)
    assert next_state.board.get(Point(3, 3)) == Player.black
    assert next_state.last_move == move
    assert next_state.previous_state == basic_game
    assert len(next_state.move_history) == 1
    assert next_state.move_history[0] == (move, Player.black)

def test_gamestate_apply_pass(basic_game):
    move = Move.pass_turn()
    next_state = basic_game.apply_move(Player.black, move)
    assert next_state.board == basic_game.board # Board unchanged
    assert next_state.last_move == move
    assert len(next_state.move_history) == 1

def test_gamestate_apply_resign(basic_game):
    move = Move.resign()
    next_state = basic_game.apply_move(Player.black, move)
    assert next_state.board == basic_game.board # Board unchanged
    assert next_state.last_move == move
    assert next_state.is_over
    assert next_state.winner() == Player.white # Opponent wins

def test_gamestate_is_valid_move_ok(basic_game):
    move = Move.play(Point(1, 1))
    assert basic_game.is_valid_move(Player.black, move)

def test_gamestate_is_valid_move_off_grid(basic_game):
    move = Move.play(Point(0, 1))
    assert not basic_game.is_valid_move(Player.black, move)
    move = Move.play(Point(6, 1))
    assert not basic_game.is_valid_move(Player.black, move)

def test_gamestate_is_valid_move_occupied(basic_game):
    play_point = Point(3, 3)
    state1 = basic_game.apply_move(Player.black, Move.play(play_point))
    move = Move.play(play_point)
    assert not state1.is_valid_move(Player.white, move)

def test_gamestate_is_valid_move_self_capture(basic_game):
    # . B .
    # B W B
    # . B .
    state = basic_game.apply_move(Player.black, Move.play(Point(1, 2)))
    state = state.apply_move(Player.black, Move.play(Point(2, 1)))
    state = state.apply_move(Player.black, Move.play(Point(2, 3)))
    state = state.apply_move(Player.black, Move.play(Point(3, 2)))

    self_capture_move = Move.play(Point(2, 2))
    assert state.is_move_self_capture(Player.white, self_capture_move)
    assert not state.is_valid_move(Player.white, self_capture_move)


def test_gamestate_is_valid_move_ko(basic_game):
    # . B W .
    # B W . .
    # . B W .
    # . . . .
    state = basic_game.apply_move(Player.black, Move.play(Point(1, 2)))
    state = state.apply_move(Player.black, Move.play(Point(2, 1)))
    state = state.apply_move(Player.black, Move.play(Point(3, 2)))
    state = state.apply_move(Player.white, Move.play(Point(1, 3)))
    state = state.apply_move(Player.white, Move.play(Point(2, 2)))
    state = state.apply_move(Player.white, Move.play(Point(3, 3)))

    capture_move = Move.play(Point(1, 1))
    state_after_capture = state.apply_move(Player.white, capture_move)
    assert state_after_capture.board.get(Point(1, 2)) is None
    ko_move = Move.play(Point(1, 2))
    assert state_after_capture.does_move_violate_ko(Player.black, ko_move)
    assert not state_after_capture.is_valid_move(Player.black, ko_move)

    state_elsewhere = state_after_capture.apply_move(Player.black, Move.play(Point(4,4)))
    state_elsewhere_2 = state_elsewhere.apply_move(Player.white, Move.play(Point(4,5)))
    assert not state_elsewhere_2.does_move_violate_ko(Player.black, ko_move)
    assert state_elsewhere_2.is_valid_move(Player.black, ko_move)

def test_gamestate_delayed_capture_pending(basic_game):
    # . B .
    # B W B
    # . B .
    state = basic_game.apply_move(Player.black, Move.play(Point(1, 2)))
    state = state.apply_move(Player.black, Move.play(Point(2, 1)))
    state = state.apply_move(Player.black, Move.play(Point(2, 3)))
    state = state.apply_move(Player.black, Move.play(Point(3, 2)))
    white_move = Move.play(Point(2,2))
    state_after_white = state.apply_move(Player.white, white_move, delayed_capture=True)
    assert state_after_white.board.get(Point(2, 2)) == Player.white

def test_gamestate_delayed_capture_resolution(basic_game):
    state = basic_game.apply_move(Player.black, Move.play(Point(1, 2)))
    state = state.apply_move(Player.black, Move.play(Point(2, 1)))
    state = state.apply_move(Player.black, Move.play(Point(2, 3)))
    state = state.apply_move(Player.black, Move.play(Point(3, 2)))
    state_after_white = state.apply_move(Player.white, Move.play(Point(2,2)), delayed_capture=True)

    board_cleaned = copy.deepcopy(state_after_white.board)
    white_group = board_cleaned.get_go_string(Point(2,2))
    if white_group:
         current_libs = {n for p in white_group.stones for n in p.neighbors() if board_cleaned.is_on_grid(n) and board_cleaned.get(n) is None}
         if not current_libs:
              board_cleaned._remove_string(white_group)


    state_cleaned = GameState(
        board=board_cleaned,
        previous=state_after_white.previous_state,
        move=state_after_white.last_move,
        move_history=state_after_white.move_history,
        pending_opponent_captures=frozenset(), # Assume cleared after resolution
        pending_self_capture=None
    )
    state_cleaned.previous_states = state_after_white.previous_states | {state_after_white.board.zobrist_hash()}
    black_move = Move.play(Point(4, 4))
    final_state = state_cleaned.apply_move(Player.black, black_move, delayed_capture=True)

    assert final_state.board.get(Point(2, 2)) is None # White stone should be gone
    assert final_state.board.get(Point(4, 4)) == Player.black # Black's move is placed

def test_gamestate_is_over_two_passes(basic_game):
    state1 = basic_game.apply_move(Player.black, Move.pass_turn())
    assert not state1.is_over
    state2 = state1.apply_move(Player.white, Move.pass_turn())
    assert state2.is_over
    assert state2.winner() is not None

def test_gamestate_winner_resign(basic_game):
    state = basic_game.apply_move(Player.black, Move.resign())
    assert state.is_over
    assert state.winner() == Player.white

def test_gamestate_winner_score(basic_game):
    # B B . . .
    # B B . . .
    # . . W W .
    # . . W W .
    # . . . . .
    state = basic_game.apply_move(Player.black, Move.play(Point(1,1)))
    state = state.apply_move(Player.black, Move.play(Point(1,2)))
    state = state.apply_move(Player.black, Move.play(Point(2,1)))
    state = state.apply_move(Player.black, Move.play(Point(2,2)))
    state = state.apply_move(Player.white, Move.play(Point(3,3)))
    state = state.apply_move(Player.white, Move.play(Point(3,4)))
    state = state.apply_move(Player.white, Move.play(Point(4,3)))
    state = state.apply_move(Player.white, Move.play(Point(4,4)))
    state = state.apply_move(Player.black, Move.pass_turn())
    state = state.apply_move(Player.white, Move.pass_turn())

    assert state.is_over
    assert state.winner() == Player.white


def test_dqueue_init():
    q = DeterministicQueue("BW")
    assert q.pattern == [Player.black, Player.white]
    assert q.current_index == 0

def test_dqueue_init_empty():
    with pytest.raises(ValueError):
        DeterministicQueue("")

def test_dqueue_init_invalid_char():
     with pytest.raises(ValueError):
        DeterministicQueue("BXW")

def test_dqueue_peek_advance_bw():
    q = DeterministicQueue("BW")
    assert q.peek_next_player() == Player.black
    assert q.current_index == 0
    q.advance_turn()
    assert q.peek_next_player() == Player.white
    assert q.current_index == 1
    q.advance_turn()
    assert q.peek_next_player() == Player.black
    assert q.current_index == 0

def test_dqueue_next_player_bbw():
    q = DeterministicQueue("BBW")
    assert q.next_player() == Player.black
    assert q.next_player() == Player.black
    assert q.next_player() == Player.white
    assert q.next_player() == Player.black

def test_dqueue_reset():
    q = DeterministicQueue("BWBWBW")
    q.advance_turn()
    q.advance_turn()
    assert q.current_index == 2
    q.reset()
    assert q.current_index == 0
    assert q.peek_next_player() == Player.black


def test_rqueue_init():
    q = RandomQueue(seed=123, chunk_size=10)
    assert len(q._sequence) == 10
    assert q._index == 0

def test_rqueue_peek_advance():
    q = RandomQueue(seed=456, chunk_size=5)
    players = []
    for _ in range(7): # Go past chunk size
        players.append(q.peek_next_player())
        q.advance_turn()
    assert len(players) == 7
    assert len(q._sequence) == 10
    assert q._index == 7

def test_rqueue_reset_reproducible():
    seed = 789
    chunk = 8
    q1 = RandomQueue(seed=seed, chunk_size=chunk)
    seq1 = [q1.next_player() for _ in range(chunk + 2)]

    q2 = RandomQueue(seed=seed, chunk_size=chunk)
    seq2 = [q2.next_player() for _ in range(chunk + 2)]

    assert seq1 == seq2


def test_setupstate_init():
    s = SetupState(19, 19)
    assert s.num_rows == 19
    assert s.num_cols == 19
    assert len(s._positions) == 0

def test_setupstate_place_get():
    s = SetupState(9, 9)
    p1 = Point(4, 4)
    p2 = Point(5, 5)
    s.place_stone(Player.black, p1)
    s.place_stone(Player.white, p2)
    positions = s.get_positions()
    assert len(positions) == 2
    assert positions[p1] == Player.black
    assert positions[p2] == Player.white

def test_setupstate_remove():
    s = SetupState(9, 9)
    p1 = Point(4, 4)
    s.place_stone(Player.black, p1)
    assert p1 in s.get_positions()
    s.remove_stone(p1)
    assert p1 not in s.get_positions()
    s.remove_stone(Point(1,1))


def test_scoring_empty_board():
    setup = SetupState(5, 5)
    gs = GameState.from_setup(setup)
    gs = gs.apply_move(Player.black, Move.pass_turn())
    gs = gs.apply_move(Player.white, Move.pass_turn())
    result = compute_game_result(gs)
    territory = evaluate_territory(gs.board)
    assert territory.num_black_stones == 0
    assert territory.num_white_stones == 0
    assert territory.num_black_territory == 0
    assert territory.num_white_territory == 0
    assert result.winner == Player.white
    assert result.winning_margin == 7.5

def test_scoring_simple_territory(basic_game):
    # B B . .
    # B B . .
    # . . W W
    # . . W W
    state = basic_game.apply_move(Player.black, Move.play(Point(1,1)))
    state = state.apply_move(Player.black, Move.play(Point(1,2)))
    state = state.apply_move(Player.black, Move.play(Point(2,1)))
    state = state.apply_move(Player.black, Move.play(Point(2,2)))
    state = state.apply_move(Player.white, Move.play(Point(3,3)))
    state = state.apply_move(Player.white, Move.play(Point(3,4)))
    state = state.apply_move(Player.white, Move.play(Point(4,3)))
    state = state.apply_move(Player.white, Move.play(Point(4,4)))
    state = state.apply_move(Player.black, Move.pass_turn())
    state = state.apply_move(Player.white, Move.pass_turn())
    result = compute_game_result(state)
    territory = evaluate_territory(state.board)
    assert territory.num_black_stones == 4
    assert territory.num_white_stones == 4
    assert result.winner == Player.white
    assert result.winning_margin == 7.5

def test_is_point_an_eye_simple(basic_game):
    # . B .
    # B E B
    # . B .
    state = basic_game.apply_move(Player.black, Move.play(Point(1,2)))
    state = state.apply_move(Player.black, Move.play(Point(2,1)))
    state = state.apply_move(Player.black, Move.play(Point(2,3)))
    state = state.apply_move(Player.black, Move.play(Point(3,2)))
    eye_point = Point(2,2)
    assert state.board.get(eye_point) is None
    assert is_point_an_eye(state.board, eye_point, Player.black)


def test_is_point_an_eye_occupied(basic_game):
    state = basic_game.apply_move(Player.black, Move.play(Point(2,2)))
    assert not is_point_an_eye(state.board, Point(2,2), Player.black)