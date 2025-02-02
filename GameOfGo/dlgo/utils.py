import platform
import subprocess
import numpy as np
from dlgo import gotypes


COLS = 'ABCDEFGHJKLMNOPQRST'
STONE_TO_CHAR = {
    None: ' . ',
    gotypes.Player.black: ' ● ',
    gotypes.Player.white: ' ○ ',
}


def print_move(player, move):
    if move.is_pass:
        move_str = 'passes'
    elif move.is_resign:
        move_str = 'resigns'
    else:
        move_str = f'{COLS[move.point.col - 1]}{move.point.row}'
    print(f'{player} {move_str}')


def print_board(board):
    header = '   ' + ' '.join(f' {col} ' for col in COLS[:board.num_cols])
    print(header)
    print('  ' + '-' * (len(header) - 2))

    for row in range(board.num_rows, 0, -1):
        row_str = f'{row:2d} |'
        for col in range(1, board.num_cols + 1):
            stone = board.get(gotypes.Point(row=row, col=col))
            row_str += STONE_TO_CHAR[stone]
        row_str += '|'
        print(row_str)
    print('  ' + '-' * (len(header) - 2))


def point_from_coords(coords):
    col = COLS.index(coords[0].upper()) + 1
    row = int(coords[1:])
    return gotypes.Point(row=row, col=col)


def coords_from_point(point):
    return f'{COLS[point.col - 1]}{point.row}'


def clear_screen():
    if platform.system() == "Windows":
        subprocess.call("cls", shell=True)
    else:
        print("\033[2J\033[H", end="")


class MoveAge:
    def __init__(self, board):
        self.move_ages = -np.ones((board.num_rows, board.num_cols), dtype=int)

    def get(self, row, col):
        return self.move_ages[row, col]

    def reset_age(self, point):
        self.move_ages[point.row - 1, point.col - 1] = -1

    def add(self, point):
        self.move_ages[point.row - 1, point.col - 1] = 0

    def increment_all(self):
        self.move_ages[self.move_ages > -1] += 1
