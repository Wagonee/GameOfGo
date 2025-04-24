from core import agent
from core.agent import random_bot
from core.goboard import GameState, Move
from core.gotypes import Player, Point
from core.scoring import compute_game_result
from core.utils import print_board, print_move, clear_screen
from core.setup_mode import SetupState

import time


def main():
    board_size = 9
    setup = SetupState(board_size, board_size)
    game = GameState.from_setup(setup)

    bots = {
        Player.black: agent.random_bot.RandomBot(),
        Player.white: agent.random_bot.RandomBot(),
    }

    current_player = Player.black

    while not game.is_over:
        time.sleep(0.3)

        clear_screen()
        game_result = compute_game_result(game)
        print(f"Score: {game_result}\n")
        print_board(game.board)

        bot_move = bots[current_player].select_move(game, current_player)
        print_move(current_player, bot_move)

        game = game.apply_move(current_player, bot_move)
        current_player = current_player.other

    clear_screen()
    final_result = compute_game_result(game)
    print(f"Game Over!\nFinal Score: {final_result}")
    print_board(game.board)
    winner = game.winner()
    print(f"Winner: {winner.name if winner else 'Draw/Undetermined'}")


if __name__ == '__main__':
    main()