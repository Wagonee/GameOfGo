from dlgo import agent
from dlgo.agent import random_bot
from dlgo import goboard
from dlgo import gotypes
from dlgo import scoring
from dlgo.utils import print_board, print_move, clear_screen

import time

from dlgo.game_turn import DeterministicQueue

def main():
    board_size = 9
    game = goboard.GameState.new_game(board_size)
    bots = {
        gotypes.Player.black: agent.random_bot.RandomBot(),
        gotypes.Player.white: agent.random_bot.RandomBot(),
    }

    queue = DeterministicQueue("BWBBWW")

    while not game.is_over:
        time.sleep(0.3)

        clear_screen()
        print(scoring.compute_game_result(game), '\n')
        print_board(game.board)

        # Получаем следующий ход из очереди
        next_turn = queue.get_next_turn()
        if next_turn is None:
            bot_move = bots[game.next_player].select_move(game)
            queue.add_turn(bot_move)
            next_turn = queue.get_next_turn()

        print_move(next_turn.player, next_turn.move)
        game = game.apply_move(next_turn.move)


if __name__ == '__main__':
    main()