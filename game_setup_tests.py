import dlgo.goboard as goboard
import dlgo.gotypes as gotypes
from dlgo.utils import print_board

game = goboard.GameState.new_game(9)

game = game.apply_move(goboard.Move.play(gotypes.Point(3, 3)))
print_board(game.board)

game = game.apply_move(goboard.Move.play(gotypes.Point(4, 4)))
print_board(game.board)

game = game.apply_move(goboard.Move.play(gotypes.Point(4, 3)))
game.board.remove_stone(
    gotypes.Point(3, 3)
)

game.complete_setup()

