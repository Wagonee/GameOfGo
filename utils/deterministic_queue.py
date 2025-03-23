from core.types import Player


class MoveQueue:
    def next_player(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


def _char_to_player(char):
    if char == "Ч":
        return Player.black
    elif char == "Б":
        return Player.white
    else:
        raise ValueError("Invalid char")


class DeterministicQueue(MoveQueue):
    def __init__(self, sequence):
        if not sequence:
            raise ValueError("Sequence cannot be empty")
        self.sequence = [_char_to_player(c) for c in sequence]
        self.index = 0

    def next_player(self):
        player = self.sequence[self.index]
        self.index = (self.index + 1) % len(self.sequence)
        return player

    def reset(self):
        self.index = 0
