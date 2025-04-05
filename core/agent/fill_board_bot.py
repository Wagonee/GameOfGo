import random
from core.goboard import Move


class FillBoardBot:
    def select_move(self, game_state):
        legal = game_state.legal_moves()
        play_moves = [m for m in legal if m.is_play]
        if play_moves:
            return random.choice(play_moves)
        else:
            pass_moves = [m for m in legal if m.is_pass]
            if pass_moves:
                return pass_moves[0]
            resign_moves = [m for m in legal if m.is_resign]
            if resign_moves:
                return resign_moves[0]
            return Move.pass_turn()
