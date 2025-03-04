from dlgo.goboard import GameState
from dlgo.gotypes import Player
from dlgo.agent.fill_board_bot import FillBoardBot
from dlgo.utils import print_board
import time

board_size = 5
game = GameState.new_game(board_size)

black_player = FillBoardBot()
white_player = FillBoardBot()

print_board(game.board)

while not game.is_over or game.board.count_empty_points == 1:
    time.sleep(0.5)
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
