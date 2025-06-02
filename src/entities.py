from typing import Optional

class Cell:
    def __init__(self, row: int, col: int, is_black: bool = False):
        """
        Represents a single cell in the crossword grid.

        Args:
            row: Row index of the cell.
            col: Column index of the cell.
            is_black: True if this cell is blacked-out (no letter allowed).
        """
        self.row = row
        self.col = col
        self.is_black = is_black
        self.char: Optional[str] = None  # The letter filled in, or None
        self.across_id: Optional[int] = None  # Number of the across clue
        self.down_id: Optional[int] = None    # Number of the down clue

class Clue:
    def __init__(
        self,
        number: int,
        direction: str,  # 'A' or 'D'
        text: str,
        length: int,
        start_row: int,
        start_col: int,
        candidates: list[tuple[str, int]] = []
    ):
        """
        Represents an Across or Down clue in the crossword.

        Args:
            number: Clue number within its direction (not globally unique).
            direction: 'across' or 'down'.
            text: The clue text.
            length: Number of letters in the answer.
            start_row: Starting row index of the answer.
            start_col: Starting column index of the answer.
        """
        self.number = number
        self.direction = direction
        self.text = text
        self.length = length
        self.start = (start_row, start_col)
        self.candidates: list[tuple[str, int]] = candidates  # Possible answers
        self.assigned: Optional[str] = None           # Chosen answer

class Grid:
    def __init__(self, pattern: list[str], clues: list[Clue], candidates: Optional[dict[tuple[int, str], list[tuple[str, int]]]] = None):
        """
        Build a grid of Cells from the provided pattern list.
        Optionally assign candidates to clues from a provided dictionary.

        Args:
            pattern: List of strings with '#' for black squares and '*' for unknown squares.
        """
        self.grid: list[list[Cell]] = []
        self.clues: list[Clue] = clues

        for r, row in enumerate(pattern):
            grid_row: list[Cell] = []
            for c, ch in enumerate(row):
                is_black = (ch == '#')
                cell = Cell(r, c, is_black=is_black)
                if not is_black:
                    # Set char to None for empty cells (represented by '*')
                    cell.char = None if ch == '*' else ch
                grid_row.append(cell)
            self.grid.append(grid_row)

        # Assign candidates to clues if provided
        if candidates is not None:
            for clue in self.clues:
                key = (clue.number, clue.direction)
                if key in candidates:
                    clue.candidates = candidates[key]

    def display_cell_char(self, cell: Cell) -> str:
        """
        Return the display character for a cell: '#' for black squares, the letter if present,
        or '*' as a placeholder for empty cells.
        """
        if cell.is_black:
            return '#'
        return cell.char if cell.char is not None else '*'

    def print(self):
        # Print the sample grid for verification using concise syntax
        for row in self.grid:
            # Use helper for readability
            print(' '.join(self.display_cell_char(cell) for cell in row))

    def print_clues(self):
        print("Across Clues:")
        for clue in self.clues:
            if clue.direction == 'A':
                print(f"{clue.number} Across ({clue.length}): {clue.text} --> {clue.assigned}")

        print("Down Clues:")
        for clue in self.clues:
            if clue.direction == 'D':
                print(f"{clue.number} Down ({clue.length}): {clue.text} --> {clue.assigned}")

    # Extract an answer from the grid for a given clue
    def get_answer(self, clue: Clue) -> str:
        """
        Read letters from the grid for the given clue, returning a string.
        Uses '*' for any empty cell to avoid None values.
        """
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        letters: list[str] = []
        for _ in range(clue.length):
            ch = self.grid[r][c].char
            letters.append(ch if ch is not None else '*')
            r += dr; c += dc
        return ''.join(letters)


