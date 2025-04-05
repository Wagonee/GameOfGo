from core.goboard import GameState
from core.gotypes import Player
from core.agent.fill_board_bot import FillBoardBot
from core.utils import print_board
import time

board_size = 5
game = GameState.new_game(board_size)

black_player = FillBoardBot()
white_player = FillBoardBot()

print_board(game.board)

while not game.is_over and game.board.count_empty_points != 1:
    time.sleep(0.1)
    if game.next_player == Player.black:
        move = black_player.select_move(game)
    else:
        move = white_player.select_move(game)
    game = game.apply_move(move)
    print_board(game.board)
    print(game.board.count_empty_points)
    print(len(game.board._grid))

print('Игра завершена!')

print(game.board.count_empty_points)
print(len(game.board._grid))

print('Игра завершена!')
game.print_history()
# print(len(game.move_history))
