import copy

from dlgo import zobrist
from dlgo.gotypes import Player, Point
from dlgo.scoring import compute_game_result

__all__ = [
    'Board',
    'GameState',
    'Move'
]


class IllegalMoveError(Exception):
    pass


class GoString:
    def __init__(self, color, stones, liberties):
        self.color = color
        self.stones = frozenset(stones)
        self.liberties = frozenset(liberties)

    def without_liberty(self, point):
        new_liberties = self.liberties - {point}
        return GoString(self.color, self.stones, new_liberties)

    def with_liberty(self, point):
        new_liberties = self.liberties | {point}
        return GoString(self.color, self.stones, new_liberties)

    def merged_with(self, string):
        assert string.color == self.color
        combined_stones = self.stones | string.stones
        return GoString(
            self.color,
            combined_stones,
            (self.liberties | string.liberties) - combined_stones)

    @property
    def num_liberties(self):
        return len(self.liberties)

    def __eq__(self, other):
        return isinstance(other, GoString) and \
            self.color == other.color and \
            self.stones == other.stones and \
            self.liberties == other.liberties

    def __deepcopy__(self, memodict=None):
        if memodict is None:
            self.memodict = {}
        return GoString(self.color, self.stones, copy.deepcopy(self.liberties))


class Board:
    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self._grid = {}
        self._hash = zobrist.EMPTY_BOARD

    def is_full(self):
        return self.count_empty_points == 0

    @property
    def count_empty_points(self):
        empty_count = 0
        for row in range(1, self.num_rows + 1):
            for col in range(1, self.num_cols + 1):
                point = Point(row, col)
                val = self._grid.get(point, None)
                if val is None:
                    empty_count += 1
        return empty_count

    # def remove_stone(self, point):
    #     if point in self._grid:
    #         removed_string = self._grid.pop(point) # Удаляем камень.
    #         color = self._grid[point].color  # Получаем цвет камня
    #         del self._grid[point]  # Удаляем только этот камень
    #         self._hash ^= zobrist.HASH_CODE[point, color]
    #     else:
    #         raise IllegalMoveError("Can't remove stone", point)

    def place_stone(self, player, point):
        assert self.is_on_grid(point)
        if self._grid.get(point) is not None:
            print('Illegal play on %s' % str(point))
            raise IllegalMoveError('Stone already in place:', point)
        adjacent_same_color = []
        adjacent_opposite_color = []
        liberties = []

        for neighbor in point.neighbors():
            if not self.is_on_grid(neighbor):
                continue
            neighbor_string = self._grid.get(neighbor)
            if neighbor_string is None:
                liberties.append(neighbor)
            elif neighbor_string.color == player:
                if neighbor_string not in adjacent_same_color:
                    adjacent_same_color.append(neighbor_string)
            else:
                if neighbor_string not in adjacent_opposite_color:
                    adjacent_opposite_color.append(neighbor_string)

        new_string = GoString(player, [point], liberties)

        for same_color_string in adjacent_same_color:
            new_string = new_string.merged_with(same_color_string)

        for new_string_point in new_string.stones:
            self._grid[new_string_point] = new_string

        self._hash ^= zobrist.HASH_CODE[point, player]

        for other_color_string in adjacent_opposite_color:
            replacement = other_color_string.without_liberty(point)
            if replacement.num_liberties:
                self._replace_string(replacement)
            else:
                self._remove_string(other_color_string)

    def _replace_string(self, new_string):
        for point in new_string.stones:
            self._grid[point] = new_string

    def _remove_string(self, string):
        for point in string.stones:
            # Добавляем свободы всем соседним группам
            for neighbor in point.neighbors():
                neighbor_string = self._grid.get(neighbor)
                if neighbor_string is None:
                    continue
                if neighbor_string is not string:
                    self._replace_string(neighbor_string.with_liberty(point))
            self._grid[point] = None
            self._hash ^= zobrist.HASH_CODE[point, string.color]

    def is_on_grid(self, point):
        return 1 <= point.row <= self.num_rows and \
            1 <= point.col <= self.num_cols

    def get(self, point):
        string = self._grid.get(point)
        if string is None:
            return None
        return string.color

    def get_go_string(self, point):
        return self._grid.get(point)

    def __eq__(self, other):
        return isinstance(other, Board) and \
            self.num_rows == other.num_rows and \
            self.num_cols == other.num_cols and \
            self._hash == other._hash

    def __deepcopy__(self, memodict=None):
        if memodict is None:
            self.memodict = {}
        copied = Board(self.num_rows, self.num_cols)
        copied._grid = copy.copy(self._grid)
        copied._hash = self._hash
        return copied

    def zobrist_hash(self):
        return self._hash


class Move:
    def __init__(self, point=None, is_pass=False, is_resign=False):
        assert (point is not None) ^ is_pass ^ is_resign, "Move is not correct!"
        self.point = point
        self.is_play = (self.point is not None)
        self.is_pass = is_pass
        self.is_resign = is_resign

    @classmethod
    def play(cls, point):
        return Move(point=point)

    @classmethod
    def pass_turn(cls):
        return Move(is_pass=True)

    @classmethod
    def resign(cls):
        return Move(is_resign=True)

    def __str__(self):
        if self.is_pass:
            return 'pass'
        if self.is_resign:
            return 'resign'
        return '(r %d, c %d)' % (self.point.row, self.point.col)


def board_from_positions(num_rows, num_cols, positions):
    board = Board(num_rows, num_cols)
    for point, color in positions.items():
        board.place_stone(color, point)
    return board


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
        # self.setup_complete = False
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

    # def complete_setup(self):
    #     self.setup_complete = True

    @classmethod
    def from_setup(cls, setup_state, next_player):
        positions = setup_state.get_positions()
        board = board_from_positions(setup_state.num_rows,
                                     setup_state.num_cols,
                                     positions)
        return GameState(board, next_player, None, None, [])

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
                    self.move_history[-1][0].is_pass and self.move_history[-2][0].is_pass):
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
        for move in self.move_history:
            print(move[0], move[1])

    def winner(self):
        if not self.is_over:
            return None
        if self.last_move.is_resign:
            return self.next_player
        game_result = compute_game_result(self)
        return game_result.winner
