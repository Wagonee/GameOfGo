from core.gotypes import Point, Player
from collections import namedtuple


class Territory:
    def __init__(self, territory_map):
        self.num_black_territory = 0
        self.num_white_territory = 0
        self.num_black_stones = 0
        self.num_white_stones = 0
        self.num_dame = 0
        self.dame_points = []

        for point, status in territory_map.items():
            if status == Player.black:
                self.num_black_stones += 1
            elif status == Player.white:
                self.num_white_stones += 1
            elif status == 'territory_b':
                self.num_black_territory += 1
            elif status == 'territory_w':
                self.num_white_territory += 1
            elif status == 'dame':
                self.num_dame += 1
                self.dame_points.append(point)


class GameResult(namedtuple('GameResult', 'b w komi')):
    @property
    def winner(self):
        # Победитель определяется по разнице очков с учётом компенсаторного очка (komi)
        if self.b > self.w + self.komi:
            return Player.black
        return Player.white

    @property
    def winning_margin(self):
        total_white = self.w + self.komi
        return abs(self.b - total_white)

    def __str__(self):
        total_white = self.w + self.komi
        if self.b > total_white:
            return f'B+{self.b - total_white:.1f}'
        return f'W+{total_white - self.b:.1f}'


def evaluate_territory(board):
    status = {}
    for r in range(1, board.num_rows + 1):
        for c in range(1, board.num_cols + 1):
            p = Point(row=r, col=c)
            if p in status:
                continue

            stone = board.get(p)
            if stone is not None:
                status[p] = stone
            else:
                group, neighbor_stones = _collect_region_iterative(p, board)
                if len(neighbor_stones) == 1:
                    owner = neighbor_stones.pop()
                    fill_status = 'territory_b' if owner == Player.black else 'territory_w'
                else:
                    fill_status = 'dame'
                for pos in group:
                    status[pos] = fill_status
    return Territory(status)


def _collect_region_iterative(start_pos, board):
    region = []
    borders = set()
    visited = set()

    stack = [start_pos]
    visited.add(start_pos)

    while stack:
        pos = stack.pop()
        region.append(pos)
        for delta_r, delta_c in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            next_pos = Point(row=pos.row + delta_r, col=pos.col + delta_c)
            if not board.is_on_grid(next_pos):
                continue
            neighbor = board.get(next_pos)
            if neighbor is None:
                if next_pos not in visited:
                    visited.add(next_pos)
                    stack.append(next_pos)
            else:
                borders.add(neighbor)
    return region, borders


def compute_game_result(game_state):
    territory = evaluate_territory(game_state.board)
    black_score = territory.num_black_territory + territory.num_black_stones
    white_score = territory.num_white_territory + territory.num_white_stones
    return GameResult(black_score, white_score, komi=7.5)
