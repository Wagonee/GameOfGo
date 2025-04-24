import random
from core.goboard import Move
from core.agent.base import Agent

class FillBoardBot(Agent):
    def select_move(self, game_state, player):
        legal = game_state.legal_moves(player)
        play_moves = [m for m in legal if m.is_play]

        if play_moves:
            return random.choice(play_moves)
        else:
            pass_moves = [m for m in legal if m.is_pass]
            if pass_moves:
                return pass_moves[0]
            resign_moves = [m for m in legal if m.is_resign]
            if resign_moves:
                return Move.pass_turn()
            return Move.pass_turn()