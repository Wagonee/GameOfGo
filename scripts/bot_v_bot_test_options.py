from core.goboard import GameState, Move
from core.gotypes import Player
from core.agent.fill_board_bot import FillBoardBot
from core.utils import print_board
from core.setup_mode import SetupState
import time

board_size = 5
game = GameState.from_setup(SetupState(board_size, board_size))

black_player_agent = FillBoardBot()
white_player_agent = FillBoardBot()

print("Initial Board:")
print_board(game.board)
print("-" * 20)

current_player = Player.black
move_count = 0
max_moves = board_size * board_size + 10

while not game.is_over and game.board.count_empty_points > 0 and move_count < max_moves:
    time.sleep(0.1)
    if current_player == Player.black:
        move = black_player_agent.select_move(game, current_player)
    else:
        move = white_player_agent.select_move(game, current_player)

    if move is None:
         print(f"{current_player.name} cannot move, passing.")
         move = Move.pass_turn()

    print(f"Move {move_count + 1}: {current_player.name} plays {move}")
    try:
        game = game.apply_move(current_player, move)
        print_board(game.board)
        print(f"Empty points: {game.board.count_empty_points}")
        print(f"Stones on board: {len(game.board._grid)}")
        print("-" * 20)

        current_player = current_player.other
        move_count += 1
    except Exception as e:
        print(f"Error applying move {move} for {current_player.name}: {e}")
        print("Trying to pass instead.")
        try:
            game = game.apply_move(current_player, Move.pass_turn())
            current_player = current_player.other
            move_count += 1
        except Exception as e_pass:
             print(f"Error applying pass move: {e_pass}. Ending game.")
             break


print('Игра завершена!')
print(f"Final empty points: {game.board.count_empty_points}")
print(f"Final stones on board: {len(game.board._grid)}")
game.print_history()
winner = game.winner()
print(f"Winner: {winner.name if winner else 'Draw/Undetermined'}")