from core.gotypes import Player


def apply_capture_rules(board, player, adjacent_opposite_color, capture_mode):
    for other_string in adjacent_opposite_color:
        replacement = other_string.without_liberty(next(iter(other_string.stones)))

        if replacement.num_liberties:
            board._replace_string(replacement)
        else:
            if capture_mode == "both":
                board._remove_string(other_string)
            elif capture_mode == "white_only":
                if other_string.color == Player.white:
                    board._remove_string(other_string)
            elif capture_mode == "black_only":
                if other_string.color == Player.black:
                    board._remove_string(other_string)


def cleanup_delayed_captures(board, color):
    groups_to_remove = set()
    for pos, string in board._grid.items():
        if string is not None and string.color == color and string.num_liberties == 0:
            groups_to_remove.add(string)

    for group in groups_to_remove:
        board._remove_string(group)
