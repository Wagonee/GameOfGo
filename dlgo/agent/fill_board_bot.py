import random
from dlgo.goboard import Move
from dlgo.gotypes import Point

class FillBoardBot:
    def select_move(self, game_state):
        empty_points = []
        for row in range(1, game_state.board.num_rows + 1):
            for col in range(1, game_state.board.num_cols + 1):
                point = Point(row, col)
                if point not in game_state.board._grid:
                    empty_points.append(point)

        if not empty_points:
            return Move.pass_turn()
        chosen_point = random.choice(empty_points)
        return Move.play(chosen_point)