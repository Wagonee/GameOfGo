from dlgo import gotypes
from dlgo import goboard

class GameTurn:
    def __init__(self, player: gotypes.Player, move: goboard.Move):
        self.player = player
        self.move = move

    def __eq__(self, other):
        if not isinstance(other, GameTurn):
            return False
        return self.player == other.player and self.move == other.move

    def __str__(self):
        return f"{self.player} {self.move}"

class DeterministicQueue:
    """
    Детерминированная очередь ходов с настраиваемым порядком.
    """
    def __init__(self, pattern="BWBBWW"):
        """
        Инициализирует очередь с заданным шаблоном.
        Args:
            pattern (str): Строка, определяющая порядок ходов.
                           'B' - черный, 'W' - белый.
                           По умолчанию "BWBBWW".
        """
        self.queue = []
        self.pattern = pattern
        self.pattern_index = 0

    def add_turn(self, move: goboard.Move):
        player = gotypes.Player.black if self.pattern[self.pattern_index] == 'B' else gotypes.Player.white
        turn = GameTurn(player, move)
        self.queue.append(turn)
        self.pattern_index = (self.pattern_index + 1) % len(self.pattern)

    def get_next_turn(self):
        if not self.queue:
            return None
        return self.queue.pop(0)