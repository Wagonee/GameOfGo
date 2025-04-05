import random
from core.gotypes import Player
from core.deterministic_queue import MoveQueue

class RandomQueue(MoveQueue):
    def __init__(self, seed=None, chunk_size=200):
        self.seed = seed if seed is not None else random.randint(0, 1_000_000)
        self.chunk_size = chunk_size
        self._random = random.Random(self.seed)
        self._sequence = []
        self._index = 0
        self._ensure_chunk()

    def _ensure_chunk(self):
        if self._index >= len(self._sequence):
             new_chunk = [self._random.choice([Player.black, Player.white]) for _ in range(self.chunk_size)]
             self._sequence.extend(new_chunk)

    def peek_next_player(self) -> Player:
        self._ensure_chunk()
        if self._index >= len(self._sequence):
             raise IndexError("Random queue generation failed or index out of bounds.")
        return self._sequence[self._index]

    def advance_turn(self):
        self._index += 1


    def reset(self):
        self._random = random.Random(self.seed)
        self._sequence = []
        self._index = 0
        self._ensure_chunk()

    def next_player(self) -> Player:
        player = self.peek_next_player()
        self.advance_turn()
        return player