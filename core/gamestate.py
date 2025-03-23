import copy
from core.board import Board
from core.move import Move
from core.types import Player, Point
from dlgo.scoring import compute_game_result


class GameState:
    def __init__(self, board, next_player, previous, move, move_history=None):
        self.board = board
        self.next_player = next_player
        self.previous_state = previous
        if self.previous_state is None:
            self.previous_states = frozenset()
        else:
            self.previous_states = frozenset(
                previous.previous_states |
                {(previous.next_player, previous.board.zobrist_hash())})
        self.last_move = move
        if move_history is None:
            self.move_history = []
        else:
            self.move_history = move_history

    def apply_move(self, move):
        if move.is_play:
            next_board = copy.deepcopy(self.board)
            next_board.place_stone(self.next_player, move.point)
        else:
            next_board = self.board
        new_move_history = self.move_history.copy()
        new_move_history.append((move, self.next_player))
        return GameState(next_board, self.next_player.other, self, move, new_move_history)

    @classmethod
    def new_game(cls, board_size):
        if isinstance(board_size, int):
            board_size = (board_size, board_size)
        board = Board(*board_size)
        return GameState(board, Player.black, None, None, [])

    def is_move_self_capture(self, player, move):
        if not move.is_play:
            return False
        next_board = copy.deepcopy(self.board)
        next_board.place_stone(player, move.point)
        new_string = next_board.get_go_string(move.point)
        return new_string.num_liberties == 0

    @property
    def situation(self):
        return self.next_player, self.board

    def does_move_violate_ko(self, player, move):
        if not move.is_play:
            return False
        next_board = copy.deepcopy(self.board)
        next_board.place_stone(player, move.point)
        next_situation = (player.other, next_board.zobrist_hash())
        return next_situation in self.previous_states

    def is_valid_move(self, move):
        if self.is_over:
            return False
        if move.is_pass or move.is_resign:
            return True
        return (
            self.board.get(move.point) is None and
            not self.is_move_self_capture(self.next_player, move) and
            not self.does_move_violate_ko(self.next_player, move)
        )

    @property
    def is_over(self):
        if self.board.is_full():
            return True
        if len(self.move_history) >= 2:
            if self.move_history[-1][0].is_resign or (
                self.move_history[-1][0].is_pass and self.move_history[-2][0].is_pass
            ):
                return True
        return False

    def legal_moves(self):
        moves = [
            Move.play(Point(row, col))
            for row in range(1, self.board.num_rows + 1)
            for col in range(1, self.board.num_cols + 1)
            if self.is_valid_move(Move.play(Point(row, col)))
        ]
        moves.append(Move.pass_turn())
        moves.append(Move.resign())
        return moves

    def print_history(self):
        for move, player in self.move_history:
            print(move, player)

    def winner(self):
        if not self.is_over:
            return None
        if self.last_move.is_resign:
            return self.next_player
        game_result = compute_game_result(self)
        return game_result.winner
