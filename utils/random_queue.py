import random
from core.types import Player


class MoveQueue:
    def next_player(self):
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()


class RandomQueue(MoveQueue):
    def next_player(self):
        return random.choice([Player.black, Player.white])

    def reset(self):
        pass
