from core.gotypes import Player

class MoveQueue:
    def peek_next_player(self) -> Player:
        raise NotImplementedError

    def advance_turn(self):
        raise NotImplementedError

    def next_player(self) -> Player:
        player = self.peek_next_player()
        self.advance_turn()
        return player

    def reset(self):
        raise NotImplementedError


def _char_to_player(char):
    if char in ("Ч", "B", "1"):
        return Player.black
    elif char in ("Б", "W", "2"):
        return Player.white
    else:
        raise ValueError("Invalid char for player sequence: {}".format(char))


class DeterministicQueue(MoveQueue):
    def __init__(self, sequence):
        if not sequence:
            raise ValueError("Sequence cannot be empty")
        self.pattern = [_char_to_player(c) for c in sequence]
        self.current_index = 0
        self.reset()

    def peek_next_player(self) -> Player:
        if not self.pattern:
             raise IndexError("Queue pattern is empty")
        return self.pattern[self.current_index]

    def advance_turn(self):
        if not self.pattern:
             return
        self.current_index = (self.current_index + 1) % len(self.pattern)

    def reset(self):
        self.current_index = 0

    def next_player(self) -> Player:
        player = self.peek_next_player()
        self.advance_turn()
        return player