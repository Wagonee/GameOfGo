import copy
import logging
from typing import Optional, List, Literal, Set, Tuple, FrozenSet, Dict, NamedTuple
from core import zobrist
from core.gotypes import Player, Point
from core.scoring import compute_game_result
from core.setup_mode import SetupState

logger = logging.getLogger(__name__)

__all__ = [
    'Board',
    'GameState',
    'Move',
    'GoString',
    'IllegalMoveError'
]


class IllegalMoveError(Exception):
    pass


class GoString:
    def __init__(self, color, stones, liberties):
        self.color: Player = color
        self.stones: FrozenSet[Point] = frozenset(stones)
        self.liberties: FrozenSet[Point] = frozenset(liberties)

    def without_liberty(self, point: Point) -> 'GoString':
        new_liberties = self.liberties - {point}
        return GoString(self.color, self.stones, new_liberties)

    def with_liberty(self, point: Point) -> 'GoString':
        new_liberties = self.liberties | {point}
        return GoString(self.color, self.stones, new_liberties)

    def merged_with(self, string: 'GoString') -> 'GoString':
        assert string.color == self.color
        combined_stones = self.stones | string.stones
        new_liberties = (self.liberties | string.liberties) - combined_stones
        return GoString(self.color, combined_stones, new_liberties)

    @property
    def num_liberties(self) -> int:
        return len(self.liberties)

    def __eq__(self, other):
        return isinstance(other, GoString) and \
            self.color == other.color and \
            self.stones == other.stones

    def __hash__(self):
        return hash((self.color, self.stones))

    def __str__(self):
        stone_coords = sorted([(p.row, p.col) for p in self.stones])
        liberty_coords = sorted([(p.row, p.col) for p in self.liberties])
        return (f"{self.color.name} group ({len(self.stones)} stones: {stone_coords}) "
                f"with {self.num_liberties} liberties: {liberty_coords}")

    def __repr__(self):
        stone_coords = sorted([(p.row, p.col) for p in self.stones])
        return f"<GoString {self.color.name} stones={stone_coords} liberties={self.num_liberties}>"


class PotentialCaptures(NamedTuple):
    opponent_groups: FrozenSet[GoString]
    player_group: Optional[GoString]


class Board:
    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self._grid: Dict[Point, GoString] = {}
        self._hash = zobrist.EMPTY_BOARD

    def is_on_grid(self, point: Point) -> bool:
        return 1 <= point.row <= self.num_rows and \
            1 <= point.col <= self.num_cols

    def get(self, point: Point) -> Optional[Player]:
        string = self._grid.get(point)
        return string.color if string is not None else None

    def get_go_string(self, point: Point) -> Optional[GoString]:
        string = self._grid.get(point)
        if string is None:
            return None
        return self._grid.get(point)

    def _replace_string(self, new_string: GoString):
        logger.debug(f"Replacing string(s) with: {repr(new_string)}")
        for point in new_string.stones:
            self._grid[point] = new_string

    def _remove_string(self, string_to_remove: GoString):
        logger.debug(f"Physically removing string: {repr(string_to_remove)}")

        neighboring_strings_to_update: Dict[GoString, Set[Point]] = {}

        for point in string_to_remove.stones:
            if (point, string_to_remove.color) in zobrist.HASH_CODE:
                self._hash ^= zobrist.HASH_CODE[(point, string_to_remove.color)]
            else:
                logger.warning(f"Zobrist hash code not found for {(point, string_to_remove.color)}")

            if point in self._grid:
                del self._grid[point]
            else:
                logger.warning(f"Attempted to remove point {point} which is already empty in _remove_string.")

            for neighbor in point.neighbors():
                if not self.is_on_grid(neighbor): continue

                neighbor_string = self._grid.get(neighbor)
                if neighbor_string is not None:
                    if neighbor_string not in neighboring_strings_to_update:
                        neighboring_strings_to_update[neighbor_string] = set()
                    neighboring_strings_to_update[neighbor_string].add(point)

        for neighbor_string, new_liberties in neighboring_strings_to_update.items():
            representative_point = next(iter(neighbor_string.stones), None)
            if representative_point and representative_point in self._grid and self._grid[
                representative_point] == neighbor_string:
                updated_neighbor = GoString(neighbor_string.color,
                                            neighbor_string.stones,
                                            neighbor_string.liberties | new_liberties)
                self._replace_string(updated_neighbor)
                logger.debug(
                    f"String at {list(updated_neighbor.stones)[0]} gained liberties {new_liberties}, now has {updated_neighbor.num_liberties}")
            else:
                logger.warning(
                    f"Neighbor string {repr(neighbor_string)} intended for liberty update was not found or changed.")

    def place_stone(self,
                    player: Player,
                    point: Point,
                    simultaneous_capture_rule: Literal['opponent', 'both', 'self'] = 'opponent',
                    delayed_capture: bool = False
                    ) -> PotentialCaptures:
        assert self.is_on_grid(point), f"Point {point} is off the board ({self.num_rows}x{self.num_cols})"
        if self._grid.get(point) is not None:
            raise IllegalMoveError(f"Point {point} is already occupied by {self.get(point)}")

        logger.info(
            f"Attempting to place {player.name} at {point}. Sim Rule: {simultaneous_capture_rule}, Delayed: {delayed_capture}")

        adjacent_same: List[GoString] = []
        adjacent_other: List[GoString] = []
        liberties: List[Point] = []

        for neighbor in point.neighbors():
            if not self.is_on_grid(neighbor): continue
            neighbor_string = self._grid.get(neighbor)
            if neighbor_string is None:
                liberties.append(neighbor)
            elif neighbor_string.color == player:
                if neighbor_string not in adjacent_same: adjacent_same.append(neighbor_string)
            else:
                if neighbor_string not in adjacent_other: adjacent_other.append(neighbor_string)

        new_string = GoString(player, [point], frozenset(liberties))
        for same_color_string in adjacent_same:
            new_string = new_string.merged_with(same_color_string)

        self._replace_string(new_string)
        if (point, player) in zobrist.HASH_CODE:
            self._hash ^= zobrist.HASH_CODE[(point, player)]
        else:
            logger.warning(f"Zobrist hash code not found for {(point, player)}")

        opponent_groups_losing_last_lib: Set[GoString] = set()
        other_strings_updated: Dict[GoString, GoString] = {}

        for other_string in adjacent_other:
            rep_point_other = next(iter(other_string.stones), None)
            if not rep_point_other or self._grid.get(rep_point_other) != other_string:
                logger.warning(
                    f"Opponent string {repr(other_string)} changed/removed before liberty update calculation.")
                continue

            replacement = other_string.without_liberty(point)
            other_strings_updated[other_string] = replacement

            if replacement.num_liberties == 0:
                opponent_groups_losing_last_lib.add(other_string)
                logger.debug(f"Opponent group {repr(other_string)} potentially captured (0 liberties after move).")
            else:
                logger.debug(
                    f"Opponent group {repr(other_string)} loses liberty at {point}, now has {replacement.num_liberties}.")

        for original_string, updated_string in other_strings_updated.items():
            if original_string not in opponent_groups_losing_last_lib:
                rep_point_orig = next(iter(original_string.stones), None)
                if rep_point_orig and self._grid.get(rep_point_orig) == original_string:
                    self._replace_string(updated_string)
                else:
                    logger.warning(
                        f"String {repr(original_string)} intended for liberty update was already changed/removed.")

        player_group_zero_libs = new_string.num_liberties == 0
        potential_self_capture_group: Optional[GoString] = new_string if player_group_zero_libs else None
        if player_group_zero_libs:
            logger.debug(f"Player group {repr(new_string)} potentially captured itself (0 liberties after placement).")
        groups_to_remove_immediately: Set[GoString] = set()
        pending_opponent_for_return = frozenset(opponent_groups_losing_last_lib)
        pending_self_for_return = potential_self_capture_group

        if not delayed_capture:
            is_simultaneous = bool(opponent_groups_losing_last_lib) and player_group_zero_libs
            if is_simultaneous:
                logger.info(f"Immediate simultaneous capture scenario. Applying rule: '{simultaneous_capture_rule}'")
                if simultaneous_capture_rule == 'opponent':
                    groups_to_remove_immediately.update(opponent_groups_losing_last_lib)
                    pending_self_for_return = None
                elif simultaneous_capture_rule == 'both':
                    groups_to_remove_immediately.update(opponent_groups_losing_last_lib)
                    if potential_self_capture_group: groups_to_remove_immediately.add(potential_self_capture_group)
                elif simultaneous_capture_rule == 'self':
                    if potential_self_capture_group: groups_to_remove_immediately.add(potential_self_capture_group)
                    pending_opponent_for_return = frozenset()

            elif opponent_groups_losing_last_lib:
                logger.debug("Standard opponent capture scenario.")
                groups_to_remove_immediately.update(opponent_groups_losing_last_lib)
                pending_self_for_return = None

            elif player_group_zero_libs:
                logger.warning(
                    f"Self-capture move detected for {player.name} at {point} (non-simultaneous). Removing player group.")
                if potential_self_capture_group: groups_to_remove_immediately.add(potential_self_capture_group)
                pending_opponent_for_return = frozenset()

            if groups_to_remove_immediately:
                logger.info(
                    f"Groups determined for immediate removal: {[repr(g) for g in groups_to_remove_immediately]}")
                for group in groups_to_remove_immediately:
                    representative_point = next(iter(group.stones), None)
                    if representative_point:
                        current_string_at_pos = self.get_go_string(representative_point)
                        if current_string_at_pos == group:
                            logger.info(f"Finalizing immediate removal of {repr(group)}")
                            self._remove_string(group)  # Perform removal
                        else:
                            logger.warning(
                                f"Group {repr(group)} decided for immediate removal, but is no longer on board at its position or has changed ({repr(current_string_at_pos)}). Skipping removal.")
                    else:
                        logger.warning(
                            f"Group {repr(group)} decided for immediate removal, but has no representative point? Should not happen.")
            pending_opponent_for_return = frozenset()
            pending_self_for_return = None

        return PotentialCaptures(
            opponent_groups=pending_opponent_for_return if delayed_capture else frozenset(
                opponent_groups_losing_last_lib),
            player_group=pending_self_for_return if delayed_capture else potential_self_capture_group
        )

    def zobrist_hash(self):
        return self._hash

    def __deepcopy__(self, memodict=None):
        if memodict is None: memodict = {}
        if id(self) in memodict: return memodict[id(self)]

        new_board = Board(self.num_rows, self.num_cols)
        new_board._hash = self._hash
        new_board._grid = self._grid.copy()

        memodict[id(self)] = new_board
        return new_board

    def is_full(self):
        return len(self._grid) == self.num_rows * self.num_cols

    @property
    def count_empty_points(self):
        return self.num_rows * self.num_cols - len(self._grid)

    def __eq__(self, other):
        if not isinstance(other, Board): return NotImplemented
        if self.num_rows != other.num_rows or self.num_cols != other.num_cols: return False
        if self._hash != other._hash: return False
        return self._grid == other._grid


class Move:
    def __init__(self, point: Optional[Point] = None, is_pass: bool = False, is_resign: bool = False):
        assert point is not None or is_pass or is_resign, "Move must be play, pass, or resign"
        self.point = point
        self.is_play = (self.point is not None)
        self.is_pass = is_pass
        self.is_resign = is_resign

    @classmethod
    def play(cls, point: Point) -> 'Move':
        return Move(point=point)

    @classmethod
    def pass_turn(cls) -> 'Move':
        return Move(is_pass=True)

    @classmethod
    def resign(cls) -> 'Move':
        return Move(is_resign=True)

    def __str__(self):
        if self.is_pass: return 'pass'
        if self.is_resign: return 'resign'
        from .utils import COLS
        try:
            col_str = COLS[self.point.col - 1]
            return f'play {col_str}{self.point.row}'
        except IndexError:
            return f'play {self.point}'

    def __eq__(self, other):
        if not isinstance(other, Move): return NotImplemented
        if self.is_pass: return other.is_pass
        if self.is_resign: return other.is_resign
        return self.is_play and other.is_play and self.point == other.point

    def __hash__(self):
        if self.is_pass: return hash("pass")
        if self.is_resign: return hash("resign")
        return hash(self.point)

    def __repr__(self):
        if self.is_play: return f"Move.play({self.point})"
        if self.is_pass: return "Move.pass_turn()"
        if self.is_resign: return "Move.resign()"
        return "Move()"


class GameState:
    def __init__(self,
                 board: Board,
                 previous: Optional['GameState'],
                 move: Optional[Move],
                 move_history: Optional[List[Tuple[Move, Player]]] = None,
                 pending_opponent_captures: FrozenSet[GoString] = frozenset(),
                 pending_self_capture: Optional[GoString] = None
                 ):
        self.board = board
        self.previous_state = previous
        self.last_move = move
        self.move_history: List[Tuple[Move, Player]] = move_history if move_history is not None else []
        self.pending_opponent_captures = pending_opponent_captures
        self.pending_self_capture = pending_self_capture

        if self.previous_state is None:
            self.previous_states: FrozenSet[int] = frozenset()
        else:
            self.previous_states = frozenset(
                previous.previous_states | {previous.board.zobrist_hash()}
            )

    def apply_move(self,
                   player_making_move: Player,
                   move: Move,
                   simultaneous_capture_rule: Literal['opponent', 'both', 'self'] = 'opponent',
                   delayed_capture: bool = False
                   ) -> 'GameState':
        if move.is_play:
            next_board = copy.deepcopy(self.board)
            try:
                potential_captures = next_board.place_stone(
                    player_making_move, move.point,
                    simultaneous_capture_rule=simultaneous_capture_rule,
                    delayed_capture=delayed_capture
                )
            except IllegalMoveError as e:
                logger.error(f"Illegal move {move} by {player_making_move.name} in apply_move (Board level): {e}")
                raise e
        elif move.is_pass or move.is_resign:
            next_board = self.board
            potential_captures = PotentialCaptures(frozenset(), None)
        else:
            raise ValueError(f"Invalid move type received in apply_move: {move}")

        new_move_history = self.move_history + [(move, player_making_move)]

        new_pending_opponent_this_move = frozenset()
        new_pending_self_this_move = None
        if delayed_capture:
            new_pending_opponent_this_move = potential_captures.opponent_groups
            new_pending_self_this_move = potential_captures.player_group
            logger.debug(
                f"Move {move} resulted in pending captures: Opponent={len(new_pending_opponent_this_move)}, Self={bool(new_pending_self_this_move)}")

        combined_pending_opponent = self.pending_opponent_captures.union(new_pending_opponent_this_move)
        combined_pending_self = new_pending_self_this_move if new_pending_self_this_move is not None else self.pending_self_capture

        new_state = GameState(
            board=next_board,
            previous=self,
            move=move,
            move_history=new_move_history,
            pending_opponent_captures=combined_pending_opponent,
            pending_self_capture=combined_pending_self
        )
        logger.debug(
            f"Applied move {move}. New state hash: {new_state.board.zobrist_hash()}. Combined Pending captures: Opponent={len(new_state.pending_opponent_captures)}, Self={bool(new_state.pending_self_capture)}")
        return new_state

    @classmethod
    def from_setup(cls, setup_state: SetupState) -> 'GameState':
        board = Board(setup_state.num_rows, setup_state.num_cols)
        try:
            for point, color in setup_state.get_positions().items():
                board.place_stone(color, point, simultaneous_capture_rule='opponent', delayed_capture=False)
        except IllegalMoveError as e:
            logger.error(f"Error placing initial stone from setup: {e}")
            raise ValueError(f"Invalid initial setup: {e}") from e
        return GameState(board, None, None, [], frozenset(), None)

    def is_move_self_capture(self, player: Player, move: Move) -> bool:
        if not move.is_play:
            return False
        next_board = copy.deepcopy(self.board)
        try:
            potential_captures = next_board.place_stone(player, move.point,
                                                        simultaneous_capture_rule='opponent',
                                                        delayed_capture=False)
            if potential_captures.player_group:
                player_string_after_move = next_board.get_go_string(move.point)
                if player_string_after_move is None:
                    sim_board_delayed = copy.deepcopy(self.board)
                    pot_delayed = sim_board_delayed.place_stone(player, move.point,
                                                                simultaneous_capture_rule='opponent',
                                                                delayed_capture=True)

                    if pot_delayed.player_group and not pot_delayed.opponent_groups:
                        logger.debug(f"Move {move} by {player.name} IS self-capture.")
                        return True
                    else:
                        logger.debug(
                            f"Move {move} by {player.name} is NOT pure self-capture (opponent groups also captured or player group survived).")
                        return False
                else:
                    return False
            else:
                return False
        except IllegalMoveError:
            return False

    def does_move_violate_ko(self, player: Player, move: Move) -> bool:
        if not move.is_play:
            return False

        board_after_move = copy.deepcopy(self.board)
        try:
            board_after_move.place_stone(player, move.point,
                                         simultaneous_capture_rule='opponent',
                                         delayed_capture=False)

            next_situation_hash = board_after_move.zobrist_hash()

            logger.debug(
                f"Checking Ko for move {move}: next hash {next_situation_hash}. Previous states hashes in current context: {self.previous_states}")
            return next_situation_hash in self.previous_states

        except IllegalMoveError:
            return False

    def is_valid_move(self, player: Player, move: Move) -> bool:
        if self.is_over:
            logger.debug(f"Move {move} invalid: Game is over.")
            return False

        if move.is_pass or move.is_resign:
            return True
        if not move.is_play:
            logger.warning(f"is_valid_move called with invalid move type: {move}")
            return False

        point = move.point
        if not self.board.is_on_grid(point):
            logger.debug(f"Move {move} invalid: Point {point} off grid.")
            return False

        if self.board.get(point) is not None:
            logger.debug(f"Move {move} invalid: Point {point} is occupied by {self.board.get(point)}.")
            return False

        if self.is_move_self_capture(player, move):
            logger.debug(f"Move {move} invalid: Self-capture.")
            return False

        if self.does_move_violate_ko(player, move):
            logger.debug(f"Move {move} invalid: Violates Ko.")
            return False

        return True

    @property
    def is_over(self) -> bool:
        if self.board.count_empty_points == 0:
            logger.info("Game is over: board is full.")
            return True

        if self.last_move and self.last_move.is_resign:
            logger.info("Game is over: last move was resign.")
            return True

        if len(self.move_history) >= 2:
            last_move_info = self.move_history[-1]
            second_last_move_info = self.move_history[-2]
            if last_move_info[0].is_pass and second_last_move_info[0].is_pass and last_move_info[1] != second_last_move_info[1]:
                logger.info("Game is over: two consecutive passes.")
                return True
        return False

    def legal_moves(self, player: Player) -> List[Move]:
        if self.is_over:
            return []

        moves = []
        for row in range(1, self.board.num_rows + 1):
            for col in range(1, self.board.num_cols + 1):
                point = Point(row, col)
                move = Move.play(point)
                if self.is_valid_move(player, move):
                    moves.append(move)

        moves.append(Move.pass_turn())
        moves.append(Move.resign())

        return moves

    def winner(self) -> Optional[Player]:
        if not self.is_over:
            return None

        if self.last_move and self.last_move.is_resign:
            if not self.move_history: return None
            player_who_resigned = self.move_history[-1][1]
            logger.info(f"Game over: Player {player_who_resigned.name} resigned.")
            return player_who_resigned.other
        game_result = compute_game_result(self)
        logger.info(f"Game over by passes/full board. Result: {game_result}")
        return game_result.winner

    def print_history(self):
        print("Move History:")
        if not self.move_history:
            print(" (No moves yet)")
            return
        for i, (move, player) in enumerate(self.move_history):
            print(f" {i + 1}. {player.name}: {move}")

    def __deepcopy__(self, memodict=None):
        if memodict is None: memodict = {}
        if id(self) in memodict:
            return memodict[id(self)]

        new_board = copy.deepcopy(self.board, memodict)

        new_previous = None
        if self.previous_state is not None:
            new_previous = copy.deepcopy(self.previous_state, memodict)

        new_game_state = GameState(
            board=new_board,
            previous=new_previous,
            move=self.last_move,
            move_history=list(self.move_history),
            pending_opponent_captures=self.pending_opponent_captures,
            pending_self_capture=self.pending_self_capture
        )
        memodict[id(self)] = new_game_state
        return new_game_state
