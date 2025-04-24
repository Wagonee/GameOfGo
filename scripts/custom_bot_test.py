from core.gotypes import Player, Point
from core.goboard import GameState, Board, Move, IllegalMoveError, GoString
from core.agent.random_bot import RandomBot
from core.utils import print_board, print_move
from core.deterministic_queue import DeterministicQueue
from io import StringIO
import sys

def setup_custom_game(board_size, setup_positions):
    board = Board(board_size, board_size)
    try:
        for color, (row, col) in setup_positions:
            board.place_stone(color, Point(row, col),
                              simultaneous_capture_rule='opponent',
                              delayed_capture=False)
    except IllegalMoveError as e:
         print(f"Error placing initial stone {color} at ({row},{col}): {e}", file=sys.stderr)
         raise
    return GameState(board=board,
                     previous=None,
                     move=None,
                     move_history=[],
                     pending_opponent_captures=frozenset(),
                     pending_self_capture=None)


def run_game(config_name, simultaneous_rule, delayed_capture, pattern, initial_stones, log):
    log.write(f"===== Scenario: {config_name} =====\n")
    log.write(f"simultaneous_rule = {simultaneous_rule}, delayed_capture = {delayed_capture}, queue: {pattern}\n\n")

    board_size = 4
    try:
        game = setup_custom_game(board_size, initial_stones)
    except IllegalMoveError:
         log.write("Error creating initial board.\n")
         log.write("=" * 40 + "\n")
         return

    bots = {
        Player.black: RandomBot(),
        Player.white: RandomBot(),
    }

    move_queue = DeterministicQueue(pattern)

    original_stdout = sys.stdout
    sys.stdout = log
    print("Initial Board:")
    print_board(game.board)
    print("Starting game!\n")

    move_number = 1
    max_moves = board_size * board_size * 2

    while not game.is_over and move_number <= max_moves:
        next_player = move_queue.next_player()
        move = bots[next_player].select_move(game, next_player)

        if not game.is_valid_move(next_player, move):
             print(f"Move {move_number}: Player {next_player.name} selected invalid move {move}. Skipping turn.")
             move = Move.pass_turn()
             if not game.is_valid_move(next_player, move):
                 print("Pass is also invalid? Ending game.")
                 break

        print(f"Move {move_number}: ", end="")
        print_move(next_player, move)

        try:
            game = game.apply_move(
                player_making_move=next_player,
                move=move,
                simultaneous_capture_rule=simultaneous_rule,
                delayed_capture=delayed_capture
            )
            print_board(game.board)
            if game.pending_opponent_captures or game.pending_self_capture:
                print(f"  Pending Opponent Captures: {len(game.pending_opponent_captures)}")
                print(f"  Pending Self Capture: {bool(game.pending_self_capture)}")
            print("-" * 20)

        except IllegalMoveError as e:
            print(f"\nError applying move {move} by player {next_player.name}: {e}")
            print("Game interrupted due to error.")
            break
        except Exception as e:
             # Using English
             print(f"\nUnexpected error applying move {move}: {e}")
             break

        move_number += 1

    if move_number > max_moves:
         print("Move limit reached.")

    print("\nGame finished!")
    if game.last_move and game.last_move.is_resign:
         print(f"Reason: Player {game.move_history[-1][1].name} resigned.")
    elif len(game.move_history) >= 2 and game.move_history[-1][0].is_pass and game.move_history[-2][0].is_pass:
         print("Reason: Two consecutive passes.")
    elif game.board.count_empty_points == 0:
         print("Reason: Board is full.")

    print("Final board:")
    print_board(game.board)
    winner = game.winner()
    print(f"Winner: {winner.name if winner else 'Draw/Undetermined'}")
    print("=" * 40 + "\n")

    sys.stdout = original_stdout

def main():
    log = StringIO()

    scenarios = [
        {
            "name": "opponent_now",
            "simultaneous_rule": "opponent",
            "delayed_capture": False,
            "pattern": "BBBW",
            "stones": [
                (Player.black, (1, 1)),
                (Player.white, (1, 2)),
                (Player.black, (2, 2)),
            ]
        },
        {
            "name": "both_delayed",
            "simultaneous_rule": "both",
            "delayed_capture": True,
            "pattern": "BW",
            "stones": [
                (Player.white, (2, 1)),
                (Player.white, (1, 2)),
                (Player.black, (3, 3)),
            ]
        },
        {
            "name": "self_now",
            "simultaneous_rule": "self",
            "delayed_capture": False,
            "pattern": "WWWB",
            "stones": [
                 (Player.white, (3, 2)),
                 (Player.black, (3, 3)),
                 (Player.black, (2, 2)),
                 (Player.white, (2, 3)),
            ]
        },
         {
            "name": "opponent_delayed",
            "simultaneous_rule": "opponent",
            "delayed_capture": True,
            "pattern": "BWBWBW",
            "stones": [ (Player.black, (2,2)), (Player.white, (2,3)) ]
        }
    ]

    for scenario in scenarios:
        run_game(
            config_name=scenario["name"],
            simultaneous_rule=scenario["simultaneous_rule"],
            delayed_capture=scenario["delayed_capture"],
            pattern=scenario["pattern"],
            initial_stones=scenario["stones"],
            log=log
        )

    try:
        output_file_path = "scenario_results.txt"
        with open(output_file_path, "w", encoding="utf-8") as result_file:
            result_file.write(log.getvalue())

        print(f"Scenario results written to file: {output_file_path}")
    except IOError as e:

        print(f"Error writing to file {output_file_path}: {e}")

        print("\nScenario log output:")
        print(log.getvalue())


if __name__ == "__main__":
    main()