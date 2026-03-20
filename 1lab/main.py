from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


FILES = "abcdefgh"
RANKS = "12345678"
PROMOTION_CHOICES = {"q", "r", "b", "n", "c", "a", "s"}
ORTHOGONAL_DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAGONAL_DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
KING_DIRECTIONS = ORTHOGONAL_DIRECTIONS + DIAGONAL_DIRECTIONS
KNIGHT_OFFSETS = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1),
]


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < 8 and 0 <= col < 8


def pos_to_notation(position: tuple[int, int]) -> str:
    row, col = position
    return f"{FILES[col]}{8 - row}"


def notation_to_pos(notation: str) -> tuple[int, int]:
    if len(notation) != 2 or notation[0] not in FILES or notation[1] not in RANKS:
        raise ValueError(f"Invalid square: {notation}")
    return 8 - int(notation[1]), FILES.index(notation[0])


@dataclass
class Move:
    piece_name: str
    color: str
    start: tuple[int, int]
    end: tuple[int, int]
    captured_piece: Piece | None = None
    promotion_choice: str | None = None
    promotion_applied: Piece | None = None
    rook_start: tuple[int, int] | None = None
    rook_end: tuple[int, int] | None = None
    en_passant_capture: tuple[int, int] | None = None
    was_first_move: bool = False
    captured_was_first_move: bool = False

    def notation(self) -> str:
        suffix = f"={self.promotion_choice.upper()}" if self.promotion_choice else ""
        capture_mark = "x" if self.captured_piece else "-"
        return (
            f"{self.color[0].upper()}:{self.piece_name} "
            f"{pos_to_notation(self.start)}{capture_mark}{pos_to_notation(self.end)}{suffix}"
        )


class Piece:
    name = "Piece"
    symbol = "?"
    value = 0

    def __init__(self, color: str, position: tuple[int, int]) -> None:
        self.color = color
        self.position = position
        self.has_moved = False

    def clone(self) -> Piece:
        piece = type(self)(self.color, self.position)
        piece.has_moved = self.has_moved
        return piece

    @property
    def enemy_color(self) -> str:
        return "black" if self.color == "white" else "white"

    @property
    def display_symbol(self) -> str:
        return self.symbol if self.color == "white" else self.symbol.lower()

    def attacks(self, board: Board) -> list[tuple[int, int]]:
        return list(self.pseudo_legal_moves(board))

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        raise NotImplementedError

    def _ray_moves(
        self,
        board: Board,
        directions: Iterable[tuple[int, int]],
        max_steps: int = 8,
    ) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        for dr, dc in directions:
            for step in range(1, max_steps + 1):
                row = self.position[0] + dr * step
                col = self.position[1] + dc * step
                if not in_bounds(row, col):
                    break
                occupant = board.grid[row][col]
                if occupant is None:
                    moves.append((row, col))
                    continue
                if occupant.color != self.color:
                    moves.append((row, col))
                break
        return moves

    def _jump_moves(self, board: Board, offsets: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        for dr, dc in offsets:
            row = self.position[0] + dr
            col = self.position[1] + dc
            if not in_bounds(row, col):
                continue
            occupant = board.grid[row][col]
            if occupant is None or occupant.color != self.color:
                moves.append((row, col))
        return moves


class King(Piece):
    name = "King"
    symbol = "KI"
    value = 1000

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, KING_DIRECTIONS, 1) + board.castling_targets(self)

    def attacks(self, board: Board) -> list[tuple[int, int]]:
        return [
            (self.position[0] + dr, self.position[1] + dc)
            for dr, dc in KING_DIRECTIONS
            if in_bounds(self.position[0] + dr, self.position[1] + dc)
        ]


class Queen(Piece):
    name = "Queen"
    symbol = "Q"
    value = 9

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, KING_DIRECTIONS)


class Rook(Piece):
    name = "Rook"
    symbol = "R"
    value = 5

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, ORTHOGONAL_DIRECTIONS)


class Bishop(Piece):
    name = "Bishop"
    symbol = "B"
    value = 3

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, DIAGONAL_DIRECTIONS)


class Knight(Piece):
    name = "Knight"
    symbol = "KN"
    value = 3

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._jump_moves(board, KNIGHT_OFFSETS)


class Pawn(Piece):
    name = "Pawn"
    symbol = "P"
    value = 1

    def direction(self) -> int:
        return -1 if self.color == "white" else 1

    def start_row(self) -> int:
        return 6 if self.color == "white" else 1

    def promotion_row(self) -> int:
        return 0 if self.color == "white" else 7

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        row, col = self.position
        moves: list[tuple[int, int]] = []
        step_row = row + self.direction()
        if in_bounds(step_row, col) and board.grid[step_row][col] is None:
            moves.append((step_row, col))
            jump_row = row + 2 * self.direction()
            if row == self.start_row() and board.grid[jump_row][col] is None:
                moves.append((jump_row, col))
        for dc in (-1, 1):
            target = (row + self.direction(), col + dc)
            if not in_bounds(*target):
                continue
            occupant = board.grid[target[0]][target[1]]
            if occupant is not None and occupant.color != self.color:
                moves.append(target)
            elif board.en_passant_target == target:
                moves.append(target)
        return moves

    def attacks(self, board: Board) -> list[tuple[int, int]]:
        row, col = self.position
        return [
            (row + self.direction(), col + dc)
            for dc in (-1, 1)
            if in_bounds(row + self.direction(), col + dc)
        ]


class Chancellor(Piece):
    name = "Chancellor"
    symbol = "CH"
    value = 8

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, ORTHOGONAL_DIRECTIONS) + self._jump_moves(board, KNIGHT_OFFSETS)


class Archbishop(Piece):
    name = "Archbishop"
    symbol = "AR"
    value = 7

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, DIAGONAL_DIRECTIONS) + self._jump_moves(board, KNIGHT_OFFSETS)


class Sentinel(Piece):
    name = "Sentinel"
    symbol = "SE"
    value = 6

    def pseudo_legal_moves(self, board: Board) -> Iterable[tuple[int, int]]:
        return self._ray_moves(board, KING_DIRECTIONS, 2) + self._jump_moves(board, KNIGHT_OFFSETS)


PIECE_TYPES = {
    "king": King,
    "queen": Queen,
    "rook": Rook,
    "bishop": Bishop,
    "knight": Knight,
    "pawn": Pawn,
    "chancellor": Chancellor,
    "archbishop": Archbishop,
    "sentinel": Sentinel,
    "q": Queen,
    "r": Rook,
    "b": Bishop,
    "n": Knight,
    "c": Chancellor,
    "a": Archbishop,
    "s": Sentinel,
}


class Board:
    def __init__(self, use_fairy_pieces: bool = False) -> None:
        self.grid: list[list[Piece | None]] = [[None for _ in range(8)] for _ in range(8)]
        self.move_history: list[Move] = []
        self.current_turn = "white"
        self.en_passant_target: tuple[int, int] | None = None
        self.use_fairy_pieces = use_fairy_pieces
        self._setup()

    def _setup(self) -> None:
        back_rank: list[type[Piece]] = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        if self.use_fairy_pieces:
            back_rank = [Chancellor, Knight, Archbishop, Queen, King, Sentinel, Knight, Rook]
        for col, piece_type in enumerate(back_rank):
            self.place(piece_type("black", (0, col)))
            self.place(piece_type("white", (7, col)))
        for col in range(8):
            self.place(Pawn("black", (1, col)))
            self.place(Pawn("white", (6, col)))

    def place(self, piece: Piece) -> None:
        row, col = piece.position
        self.grid[row][col] = piece

    def get_piece(self, position: tuple[int, int]) -> Piece | None:
        return self.grid[position[0]][position[1]]

    def remove_piece(self, position: tuple[int, int]) -> Piece | None:
        piece = self.get_piece(position)
        self.grid[position[0]][position[1]] = None
        return piece

    def move_piece(self, start: tuple[int, int], end: tuple[int, int], promotion_choice: str | None = None) -> Move:
        piece = self.get_piece(start)
        if piece is None:
            raise ValueError("There is no piece on the starting square.")
        if piece.color != self.current_turn:
            raise ValueError("It is the other player's turn.")
        if end not in self.legal_moves_for_piece(start):
            raise ValueError("Illegal move for the selected piece.")

        move = Move(piece.name, piece.color, start, end, was_first_move=not piece.has_moved)
        captured_piece = self.get_piece(end)
        if isinstance(piece, Pawn) and end == self.en_passant_target and captured_piece is None:
            move.en_passant_capture = (start[0], end[1])
            captured_piece = self.remove_piece(move.en_passant_capture)
        else:
            self.remove_piece(end)

        move.captured_piece = captured_piece
        if captured_piece is not None:
            move.captured_was_first_move = not captured_piece.has_moved

        self.remove_piece(start)
        piece.position = end
        piece.has_moved = True
        self.place(piece)

        if isinstance(piece, King) and abs(end[1] - start[1]) == 2:
            rook_start, rook_end = self._castle_rook_positions(end)
            rook = self.remove_piece(rook_start)
            if rook is None:
                raise ValueError("Castling rook was not found.")
            move.rook_start, move.rook_end = rook_start, rook_end
            rook.position = rook_end
            rook.has_moved = True
            self.place(rook)

        self.en_passant_target = None
        if isinstance(piece, Pawn) and abs(end[0] - start[0]) == 2:
            self.en_passant_target = ((start[0] + end[0]) // 2, start[1])

        if isinstance(piece, Pawn) and end[0] == piece.promotion_row():
            promoted_type = PIECE_TYPES.get((promotion_choice or "q").lower(), Queen)
            promoted_piece = promoted_type(piece.color, end)
            promoted_piece.has_moved = True
            self.place(promoted_piece)
            move.promotion_choice = promoted_type.symbol
            move.promotion_applied = promoted_piece

        self.move_history.append(move)
        self.current_turn = piece.enemy_color
        return move

    def undo_last_move(self, count: int = 1) -> None:
        if count < 1:
            raise ValueError("Undo count must be positive.")
        if count > len(self.move_history):
            raise ValueError("There are not enough moves to undo.")

        for _ in range(count):
            move = self.move_history.pop()
            self.current_turn = move.color
            moved_piece = self.remove_piece(move.end)
            if moved_piece is None:
                raise ValueError("Cannot undo move: moved piece was not found.")

            if move.promotion_applied is not None:
                moved_piece = Pawn(move.color, move.end)
                moved_piece.has_moved = True

            moved_piece.position = move.start
            moved_piece.has_moved = not move.was_first_move
            self.place(moved_piece)

            if move.rook_start and move.rook_end:
                rook = self.remove_piece(move.rook_end)
                if rook is None:
                    raise ValueError("Cannot undo castling: rook was not found.")
                rook.position = move.rook_start
                rook.has_moved = False
                self.place(rook)

            if move.captured_piece is not None:
                captured = move.captured_piece
                captured.has_moved = not move.captured_was_first_move
                captured.position = move.en_passant_capture or move.end
                self.place(captured)

            self.en_passant_target = None
            if self.move_history:
                previous = self.move_history[-1]
                if previous.piece_name == "Pawn" and abs(previous.start[0] - previous.end[0]) == 2:
                    self.en_passant_target = ((previous.start[0] + previous.end[0]) // 2, previous.start[1])

    def _castle_rook_positions(self, king_end: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        row, col = king_end
        return ((row, 7), (row, 5)) if col == 6 else ((row, 0), (row, 3))

    def castling_targets(self, king: King) -> list[tuple[int, int]]:
        if king.has_moved or self.is_in_check(king.color):
            return []
        row, col = king.position
        targets: list[tuple[int, int]] = []
        for rook_col, empty_cols, target_col in ((7, [5, 6], 6), (0, [1, 2, 3], 2)):
            rook = self.get_piece((row, rook_col))
            if not isinstance(rook, Rook) or rook.color != king.color or rook.has_moved:
                continue
            if any(self.get_piece((row, current_col)) is not None for current_col in empty_cols):
                continue
            path_cols = [col, 5, 6] if target_col == 6 else [col, 3, 2]
            if any(self.square_under_attack((row, path_col), king.enemy_color) for path_col in path_cols):
                continue
            targets.append((row, target_col))
        return targets

    def square_under_attack(self, square: tuple[int, int], by_color: str) -> bool:
        return any(square in piece.attacks(self) for piece in self.pieces(by_color))

    def pieces(self, color: str | None = None) -> list[Piece]:
        return [
            piece
            for row in self.grid
            for piece in row
            if piece is not None and (color is None or piece.color == color)
        ]

    def king_position(self, color: str) -> tuple[int, int]:
        for piece in self.pieces(color):
            if isinstance(piece, King):
                return piece.position
        raise ValueError(f"King of color {color} was not found.")

    def is_in_check(self, color: str) -> bool:
        return self.square_under_attack(self.king_position(color), "black" if color == "white" else "white")

    def legal_moves_for_piece(self, position: tuple[int, int]) -> list[tuple[int, int]]:
        piece = self.get_piece(position)
        if piece is None:
            return []
        legal_moves: list[tuple[int, int]] = []
        for target in piece.pseudo_legal_moves(self):
            snapshot = self.snapshot()
            try:
                snapshot._force_move(position, target)
            except ValueError:
                continue
            if not snapshot.is_in_check(piece.color):
                legal_moves.append(target)
        return legal_moves

    def _force_move(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        piece = self.get_piece(start)
        if piece is None:
            raise ValueError("Piece is missing.")
        target_piece = self.get_piece(end)
        if isinstance(piece, Pawn) and end == self.en_passant_target and target_piece is None:
            self.remove_piece((start[0], end[1]))
        else:
            self.remove_piece(end)
        self.remove_piece(start)
        piece.position = end
        piece.has_moved = True
        self.place(piece)
        if isinstance(piece, King) and abs(end[1] - start[1]) == 2:
            rook_start, rook_end = self._castle_rook_positions(end)
            rook = self.remove_piece(rook_start)
            if rook is None:
                raise ValueError("Castling rook is missing.")
            rook.position = rook_end
            rook.has_moved = True
            self.place(rook)

    def all_legal_moves(self, color: str) -> dict[str, list[str]]:
        return {
            pos_to_notation(piece.position): [pos_to_notation(move) for move in self.legal_moves_for_piece(piece.position)]
            for piece in self.pieces(color)
            if self.legal_moves_for_piece(piece.position)
        }

    def threatened_pieces(self, color: str) -> list[Piece]:
        enemy = "black" if color == "white" else "white"
        return [piece for piece in self.pieces(color) if self.square_under_attack(piece.position, enemy)]

    def game_state(self, color: str) -> str:
        if self.all_legal_moves(color):
            return "check" if self.is_in_check(color) else "active"
        return "checkmate" if self.is_in_check(color) else "stalemate"

    def snapshot(self) -> Board:
        copied = Board(self.use_fairy_pieces)
        copied.grid = [[piece.clone() if piece else None for piece in row] for row in self.grid]
        copied.move_history = list(self.move_history)
        copied.current_turn = self.current_turn
        copied.en_passant_target = self.en_passant_target
        return copied

    def render(self, highlight_moves: set[tuple[int, int]] | None = None) -> str:
        highlight_moves = highlight_moves or set()
        threatened = {piece.position for piece in self.threatened_pieces("white")}
        threatened.update(piece.position for piece in self.threatened_pieces("black"))
        white_king = self.king_position("white")
        black_king = self.king_position("black")
        lines = ["      a   b   c   d   e   f   g   h", "   +----------------------------------------+"]
        for row in range(8):
            cells: list[str] = []
            for col in range(8):
                position = (row, col)
                piece = self.grid[row][col]
                if position in highlight_moves:
                    cell = " * "
                elif piece is None:
                    cell = " . "
                else:
                    prefix = "#" if (
                        (position == white_king and self.is_in_check("white"))
                        or (position == black_king and self.is_in_check("black"))
                    ) else ("!" if position in threatened else " ")
                    cell = f"{prefix}{piece.display_symbol}".ljust(3)
                cells.append(cell)
            lines.append(f"{8 - row} | {' '.join(cells)} |")
        lines.append("   +----------------------------------------+")
        return "\n".join(lines)


HELP_TEXT = """
Commands:
  move e2 e4         regular move
  move e7 e8 q       pawn promotion move
  moves e2           show legal moves for a piece
  board              print the board
  status             show game status
  history            show move history
  threats            show threatened pieces
  undo               undo the last move
  undo 3             undo three moves
  help               show help
  exit               quit the game
""".strip()


@dataclass
class CommandResult:
    message: str
    board_view: bool = False
    highlight: set[tuple[int, int]] | None = None


class Game:
    def __init__(self, use_fairy_pieces: bool = False) -> None:
        self.board = Board(use_fairy_pieces)

    def execute(self, raw_command: str) -> CommandResult:
        command = raw_command.strip().split()
        if not command:
            return CommandResult("Enter a command. Use `help` to see the list of actions.")

        action = command[0].lower()
        if action == "help":
            return CommandResult(HELP_TEXT)
        if action == "board":
            return CommandResult("Current board position:", board_view=True)
        if action == "status":
            return CommandResult(self._status_message())
        if action == "history":
            return CommandResult(self._history_message())
        if action == "threats":
            return CommandResult(self._threats_message())
        if action == "undo":
            count = int(command[1]) if len(command) == 2 else 1
            if len(command) not in (1, 2):
                raise ValueError("Format: undo [count]")
            self.board.undo_last_move(count)
            return CommandResult(f"{count} move(s) undone.", board_view=True)
        if action == "moves":
            if len(command) != 2:
                raise ValueError("Format: moves e2")
            position = notation_to_pos(command[1].lower())
            piece = self.board.get_piece(position)
            if piece is None:
                raise ValueError("There is no piece on that square.")
            legal = self.board.legal_moves_for_piece(position)
            if not legal:
                return CommandResult(
                    f"{piece.color.capitalize()} {piece.name} on {command[1].lower()} has no legal moves.",
                    board_view=True,
                )
            return CommandResult(
                f"{piece.color.capitalize()} {piece.name} on {command[1].lower()} can move to: "
                + ", ".join(pos_to_notation(move) for move in legal),
                board_view=True,
                highlight=set(legal),
            )
        if action == "move":
            if len(command) not in (3, 4):
                raise ValueError("Format: move e2 e4 [q|r|b|n|c|a|s]")
            promotion = command[3].lower() if len(command) == 4 else None
            if promotion and promotion not in PROMOTION_CHOICES:
                raise ValueError("Unknown promotion piece type.")
            move = self.board.move_piece(
                notation_to_pos(command[1].lower()),
                notation_to_pos(command[2].lower()),
                promotion,
            )
            return CommandResult(f"Move completed: {move.notation()}.\n{self._status_message()}", board_view=True)
        raise ValueError("Unknown command. Use `help`.")

    def _history_message(self) -> str:
        if not self.board.move_history:
            return "Move history is empty."
        return "Move history:\n" + "\n".join(
            f"{index}. {move.notation()}" for index, move in enumerate(self.board.move_history, 1)
        )

    def _threats_message(self) -> str:
        lines: list[str] = []
        for color in ("white", "black"):
            threatened = self.board.threatened_pieces(color)
            details = ", ".join(f"{piece.name}@{pos_to_notation(piece.position)}" for piece in threatened)
            lines.append(f"{color.capitalize()}: {details or 'no threatened pieces'}")
        return "\n".join(lines)

    def _status_message(self) -> str:
        color = self.board.current_turn
        state = self.board.game_state(color)
        if state == "active":
            return f"{color.capitalize()} to move. No check."
        if state == "check":
            return f"{color.capitalize()} to move. Check!"
        if state == "checkmate":
            winner = "black" if color == "white" else "white"
            return f"Checkmate. {winner.capitalize()} wins."
        return "Stalemate. Draw."

    def cli_loop(self) -> None:
        print("OOP chess. Enter `help` to see the command list.")
        print(self.board.render())
        while True:
            raw_command = input(f"[{self.board.current_turn}]> ").strip()
            if raw_command.lower() in {"exit", "quit"}:
                print("Game finished.")
                break
            try:
                result = self.execute(raw_command)
                print(result.message)
                if result.board_view:
                    print(self.board.render(result.highlight))
            except Exception as error:
                print(f"Error: {error}")


def choose_mode() -> bool:
    print("Choose mode:")
    print("1. Classic chess")
    print("2. Variant with new pieces")
    return input("> ").strip() == "2"


if __name__ == "__main__":
    Game(use_fairy_pieces=choose_mode()).cli_loop()
