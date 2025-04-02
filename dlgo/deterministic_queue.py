from dlgo.gotypes import Player


class MoveQueue:
    def next_player(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


def _char_to_player(char):
    if char in ("Ч", "B", "1"):
        return Player.black
    elif char in ("Б", "W", "2"):
        return Player.white
    else:
        raise ValueError("Invalid char: {}".format(char))


class DeterministicQueue(MoveQueue):
    def __init__(self, sequence):
        if not sequence:
            raise ValueError("Sequence cannot be empty")

        if '(' in sequence and ')' in sequence:
            start_index = sequence.index('(')
            end_index = sequence.index(')')
            self.initial_part = [_char_to_player(c) for c in sequence[:start_index]]
            self.period_part = [_char_to_player(c) for c in sequence[start_index + 1:end_index]]
            if not self.period_part:
                raise ValueError("Period part cannot be empty")
        else:
            self.initial_part = []
            self.period_part = [_char_to_player(c) for c in sequence]
        self.initial_index = 0
        self.period_index = 0
        self.reset()

    def next_player(self):
        if self.initial_index < len(self.initial_part):
            player = self.initial_part[self.initial_index]
            self.initial_index += 1
            return player

        player = self.period_part[self.period_index]
        self.period_index = (self.period_index + 1) % len(self.period_part)
        return player

    def reset(self):
        self.initial_index = 0
        self.period_index = 0
