from dlgo.gotypes import Player, Point
from dlgo.goboard import GameState, Board
from dlgo.agent.random_bot import RandomBot
from dlgo.utils import print_board, print_move
from dlgo.capture_rules import cleanup_delayed_captures
from dlgo.deterministic_queue import DeterministicQueue
from io import StringIO
import sys


def setup_custom_game(board_size, setup_positions):
    board = Board(board_size, board_size)
    for color, (row, col) in setup_positions:
        board.place_stone(color, Point(row, col))
    return GameState(board=board, next_player=Player.black, previous=None, move=None)


def run_game(config_name, capture_mode, delayed_capture, pattern, initial_stones, log):
    log.write(f"===== Сценарий: {config_name} =====\n")
    log.write(f"capture_mode = {capture_mode}, delayed_capture = {delayed_capture}, очередь: {pattern}\n\n")

    board_size = 4
    game = setup_custom_game(board_size, initial_stones)

    bots = {
        Player.black: RandomBot(),
        Player.white: RandomBot(),
    }

    move_queue = DeterministicQueue(pattern)

    original_stdout = sys.stdout
    sys.stdout = log  # перенаправляем печать в лог

    print_board(game.board)
    print("Начинаем игру!\n")

    move_number = 1
    while not game.is_over and move_number <= 30:
        next_player = move_queue.next_player()

        if delayed_capture:
            cleanup_delayed_captures(game.board, next_player)

        move = bots[next_player].select_move(game)
        print(f"Ход {move_number}: ", end="")
        print_move(next_player, move)

        game = game.apply_move(move)
        print_board(game.board)
        move_number += 1

    print("Игра завершена!\nФинальная доска:")
    print_board(game.board)
    print("=" * 40 + "\n")

    sys.stdout = original_stdout  # возвращаем stdout


def main():
    log = StringIO()

    scenarios = [
        {
            "name": "white_only_now",
            "capture_mode": "white_only",
            "delayed_capture": False,
            "pattern": "ЧЧЧБ",
            "stones": [
                (Player.black, (1, 1)),
                (Player.white, (1, 2)),
                (Player.black, (2, 2)),
            ]
        },
        {
            "name": "both_delayed",
            "capture_mode": "both",
            "delayed_capture": True,
            "pattern": "ЧБ",
            "stones": [
                (Player.black, (1, 1)),
                (Player.white, (1, 2)),
                (Player.white, (2, 1)),
                (Player.black, (3, 3)),
            ]
        },
        {
            "name": "black_only_now",
            "capture_mode": "black_only",
            "delayed_capture": False,
            "pattern": "БББЧ",
            "stones": [
                (Player.black, (3, 3)),
                (Player.black, (2, 2)),
                (Player.white, (2, 3)),
                (Player.white, (3, 2)),
            ]
        },
    ]

    for scenario in scenarios:
        run_game(
            config_name=scenario["name"],
            capture_mode=scenario["capture_mode"],
            delayed_capture=scenario["delayed_capture"],
            pattern=scenario["pattern"],
            initial_stones=scenario["stones"],
            log=log
        )

    # Сохраняем результат в файл
    with open("../scenario_results.txt", "w", encoding="utf-8") as result_file:
        result_file.write(log.getvalue())


if __name__ == "__main__":
    main()
