class SetupState:
    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self._positions = {}

    def place_stone(self, color, point):
        self._positions[point] = color

    def remove_stone(self, point):
        self._positions.pop(point, None)

    def get_positions(self):
        return dict(self._positions)
