from dlgo import agent
from dlgo.agent import random_bot
from dlgo import goboard
from dlgo import gotypes
from dlgo import scoring
from dlgo.utils import print_board, print_move, clear_screen

import time


def main():
    board_size = 9
    game = goboard.GameState.new_game(board_size)
    bots = {
        gotypes.Player.black: agent.random_bot.RandomBot(),
        gotypes.Player.white: agent.random_bot.RandomBot(),
    }
    while not game.is_over():
        time.sleep(0.3)

        clear_screen()
        print(scoring.compute_game_result(game), '\n')
        print_board(game.board)
        bot_move = bots[game.next_player].select_move(game)
        print_move(game.next_player, bot_move)
        game = game.apply_move(bot_move)


if __name__ == '__main__':
    main()
