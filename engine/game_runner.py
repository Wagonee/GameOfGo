
import time
from core.gamestate import GameState
from core.types import Player
from core.move import Move
from utils.display import print_board, print_move


class GameRunner:
    def __init__(self, board_size, black_agent, white_agent, print_fn=print, delay=0.5):
        self.board_size = board_size
        self.black_agent = black_agent
        self.white_agent = white_agent
        self.print_fn = print_fn
        self.delay = delay
        self.game = GameState.new_game(board_size)

    def run(self):
        while not self.game.is_over:
            time.sleep(self.delay)
            self.print_fn()
            print_board(self.game.board)
            agent = self.black_agent if self.game.next_player == Player.black else self.white_agent
            move = agent.select_move(self.game)
            print_move(self.game.next_player, move)
            self.game = self.game.apply_move(move)

        self.print_fn()
        print("Игра завершена!")
        print_board(self.game.board)
        print("Победитель:", self.game.winner())
