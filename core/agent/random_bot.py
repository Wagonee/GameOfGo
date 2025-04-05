import random

from core.agent.base import Agent
from core.agent.helpers import is_point_an_eye
from core.goboard import Move
from core.gotypes import Point, Player


def evaluate_move(game_state, candidate):
    score = 0

    for neighbor in candidate.neighbors():
        if not game_state.board.is_on_grid(neighbor):
            continue
        neighbor_color = game_state.board.get(neighbor)
        if neighbor_color is None:
            continue
        if neighbor_color != game_state.next_player:
            enemy_string = game_state.board.get_go_string(neighbor)
            if enemy_string is not None and enemy_string.num_liberties == 1:
                score += len(enemy_string.stones) * 2
        elif neighbor_color == game_state.next_player:
            score += 0.5

    return score


class RandomBot(Agent):
    def select_move(self, game_state):
        best_moves = []
        best_score = -float('inf')
        for r in range(1, game_state.board.num_rows + 1):
            for c in range(1, game_state.board.num_cols + 1):
                candidate = Point(r, c)
                move = Move.play(candidate)
                if not game_state.is_valid_move(move) or \
                        is_point_an_eye(game_state.board, candidate, game_state.next_player):
                    continue

                score = evaluate_move(game_state, candidate)
                if score > best_score:
                    best_score = score
                    best_moves = [candidate]
                elif score == best_score:
                    best_moves.append(candidate)
        if not best_moves:
            return Move.pass_turn()
        return Move.play(random.choice(best_moves))
