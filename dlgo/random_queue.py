import random
from dlgo.gotypes import Player


class MoveQueue:
    def next_player(self):
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()


class RandomQueue(MoveQueue):
    def __init__(self, seed=None, chunk_size=200):
        self.seed = seed or random.randint(0, 1_000_000)
        self.chunk_size = chunk_size
        self.random = random.Random(self.seed)
        self.sequence = []
        self.index = 0
        self._generate_chunk()

    def _generate_chunk(self):
        for _ in range(self.chunk_size):
            self.sequence.append(self.random.choice([Player.black, Player.white]))

    def next_player(self):
        if self.index >= len(self.sequence):
            self._generate_chunk()
        player = self.sequence[self.index]
        self.index += 1
        return player

    def reset(self):
        self.random = random.Random(self.seed)
        self.sequence = []
        self.index = 0
        self._generate_chunk()
