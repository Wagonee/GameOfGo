
import copy
from core.types import Point
from core.strings import GoString
from dlgo import zobrist  # пока оставим zobrist из старого модуля


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

    def place_stone(self, player, point):
        assert self.is_on_grid(point)
        if self._grid.get(point) is not None:
            raise ValueError(f"Point {point} is already occupied")
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
            for neighbor in point.neighbors():
                neighbor_string = self._grid.get(neighbor)
                if neighbor_string is None:
                    continue
                if neighbor_string is not string:
                    self._replace_string(neighbor_string.with_liberty(point))
            self._grid[point] = None
            self._hash ^= zobrist.HASH_CODE[point, string.color]

    def is_on_grid(self, point):
        return 1 <= point.row <= self.num_rows and 1 <= point.col <= self.num_cols

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
        copied = Board(self.num_rows, self.num_cols)
        copied._grid = copy.copy(self._grid)
        copied._hash = self._hash
        return copied

    def zobrist_hash(self):
        return self._hash
