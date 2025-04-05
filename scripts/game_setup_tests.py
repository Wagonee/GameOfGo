from core.gotypes import Player, Point
from core.goboard import GameState, Move
from core.setup_mode import SetupState
from core.utils import print_board

def main():
    setup = SetupState(9, 9)

    setup.place_stone(Player.black, Point(row=3, col=3))
    setup.place_stone(Player.white, Point(row=3, col=4))
    setup.place_stone(Player.black, Point(row=4, col=4))
    # setup.remove_stone(Point(row=3, col=4))

    game_state = GameState.from_setup(setup, Player.black)
    print_board(game_state.board)
if __name__ == '__main__':
    main()
