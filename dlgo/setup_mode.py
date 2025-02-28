from dlgo.gotypes import Player, Point

class SetupState:
    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self._positions = {}  # {Point: Player}

    def place_stone(self, color, point):
        # Проверка на выход за границы и т.д.
        self._positions[point] = color

    def remove_stone(self, point):
        self._positions.pop(point, None)

    def get_positions(self):
        # Возвращаем копию, чтобы не менять напрямую _positions
        return dict(self._positions)
