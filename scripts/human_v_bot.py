from core.agent import random_bot
from core.goboard import GameState, Move, IllegalMoveError
from core.gotypes import Player, Point
from core.utils import print_board, print_move, point_from_coords, clear_screen
from core.scoring import compute_game_result
from core.setup_mode import SetupState
from typing import Literal

def main():
    BOARD_SIZE: int = 9
    SIMULTANEOUS_RULE: Literal['opponent', 'both', 'self'] = 'opponent'
    DELAYED_CAPTURE: bool = False

    valid_rules = {'opponent', 'both', 'self'}
    if SIMULTANEOUS_RULE not in valid_rules:
        print(f"Invalid value for SIMULTANEOUS_RULE: {SIMULTANEOUS_RULE}. Use one of: {valid_rules}")
        return
    if not isinstance(DELAYED_CAPTURE, bool):
         print(f"Invalid value for DELAYED_CAPTURE: {DELAYED_CAPTURE}. Use True or False.")
         return
    if not (5 <= BOARD_SIZE <= 19):
        print(f"Invalid value for BOARD_SIZE: {BOARD_SIZE}. Allowed sizes are 5 to 19.")
        return

    print(f"Starting game with parameters:")
    print(f"  Board Size: {BOARD_SIZE}x{BOARD_SIZE}")
    print(f"  Simultaneous Capture Rule: {SIMULTANEOUS_RULE}")
    print(f"  Delayed Capture: {DELAYED_CAPTURE}")
    print("-" * 20)

    setup = SetupState(BOARD_SIZE, BOARD_SIZE)
    game = GameState.from_setup(setup)
    bot = random_bot.RandomBot()

    human_player = Player.black
    bot_player = Player.white
    current_player = human_player

    while not game.is_over:
        clear_screen()
        print_board(game.board)
        game_result = compute_game_result(game)
        print(f"\nCurrent Score: {game_result}")
        print(f"Turn: {current_player.name}")
        print(f"Rules: SimCapture={SIMULTANEOUS_RULE}, Delayed={DELAYED_CAPTURE}")

        if current_player == human_player:
            human_input = input('Your move (e.g., D4, pass, resign): ')
            input_stripped = human_input.strip().lower()

            if input_stripped == 'pass':
                move = Move.pass_turn()
            elif input_stripped == 'resign':
                move = Move.resign()
            else:
                try:
                    point = point_from_coords(input_stripped)
                    if not (1 <= point.row <= BOARD_SIZE and 1 <= point.col <= BOARD_SIZE):
                        print(f"Coordinates ({point.row},{point.col}) are off the {BOARD_SIZE}x{BOARD_SIZE} board.")
                        continue
                    move = Move.play(point)
                    if not game.is_valid_move(current_player, move):
                         print("Invalid move. Try again.")
                         continue
                except ValueError:
                    print("Invalid input format. Enter coordinates (e.g., C3), 'pass', or 'resign'.")
                    continue
                except IndexError:
                     print("Invalid coordinates.")
                     continue
        else:
            move = bot.select_move(game, current_player)
            if not game.is_valid_move(current_player, move):
                 print(f"Bot chose an invalid move ({move}), passing.")
                 move = Move.pass_turn()

        try:
            print_move(current_player, move)
            game = game.apply_move(
                player_making_move=current_player,
                move=move,
                simultaneous_capture_rule=SIMULTANEOUS_RULE,
                delayed_capture=DELAYED_CAPTURE
            )
            current_player = current_player.other

        except IllegalMoveError as e:
             print(f"Error! Illegal move: {e}")
             input("Press Enter to continue...")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

    clear_screen()
    print("="*20)
    print("Game over!")
    print("Final board:")
    print_board(game.board)
    final_result = compute_game_result(game)
    print(f"Final score: {final_result}")
    winner = game.winner()
    if winner:
        print(f"Winner: {winner.name}")
    else:
         print("Winner not determined.")
    print("="*20)


if __name__ == '__main__':
    main()