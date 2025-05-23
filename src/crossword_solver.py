from typing import Optional

# Placeholder for the real get_answers function
def get_answers(clue: str, length: int, known_letters: str) -> list[tuple[str, float]]:
    """
    Retrieve potential answers for a given crossword clue.

    Args:
        clue: The text of the crossword clue.
        length: Expected length of the answer.
        known_letters: Pattern string with known letters and '*' for unknowns.

    Returns:
        A list of tuples (word, confidence) sorted by confidence descending.
    """
    # The Clues for the test already have the correct answers provided as
    # candidates with 100% condidence.
    #raise NotImplementedError("Integrate with your answer-retrieval service here.")
    return []

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
        candidates: list[tuple[str, float]] = []
    ):
        """
        Represents an Across or Down clue in the crossword.

        Args:
            number: Clue number within its direction (not globally unique).
            direction: 'A' or 'D'.
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
        self.candidates = candidates  # Possible answers
        self.assigned: Optional[str] = None           # Chosen answer

class Grid:
    def __init__(self, pattern: list[str], clues: list[Clue]):
        """
        Build a grid of Cells from the provided pattern list.

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

class CrosswordSolver:
    def __init__(self, grid: Grid):
        """
        Initializes the crossword solver.
        Args:
            grid: 2D list of Cell objects and accociated clues.
        """
        self.grid = grid
        # Cache for get_answers results keyed by (direction, number, pattern)
        self.cache: dict[tuple[str, int, str], list[tuple[str, float]]] = {}

    def current_pattern(self, clue: Clue) -> str:
        """
        Build the current letter pattern for a clue from the grid.

        Unknown cells are represented by '*'.

        Args:
            clue: The Clue object to inspect.

        Returns:
            A string pattern of length clue.length.
        """
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        pattern: list[str] = []
        r, c = clue.start
        for _ in range(clue.length):
            ch = self.grid.grid[r][c].char or '*'
            pattern.append(ch)
            r += dr; c += dc
        return ''.join(pattern)

    def fetch_candidates(self, clue: Clue) -> list[tuple[str, float]]:
        """
        Retrieve (and cache) candidate answers for a clue using the current pattern.

        Keys the cache by (direction, number, pattern) to distinguish across vs down.
        Uses candidates from the Clue object if available, otherwise calls get_answers().

        Args:
            clue: The Clue object whose candidates to fetch.

        Returns:
            List of (word, confidence) tuples.
        """
        pattern = self.current_pattern(clue)
        key = (clue.direction, clue.number, pattern)
        if key not in self.cache:
            # Use candidates from the Clue object if available, otherwise call get_answers()
            if clue.candidates:
                candidates = clue.candidates
            else:
                candidates = get_answers(clue.text, clue.length, pattern)
            candidates.sort(key=lambda x: x[1], reverse=True)
            self.cache[key] = candidates
        return self.cache[key]

    def fits_without_conflict(self, clue: Clue, word: str) -> bool:
        """
        Check if placing a word for a clue conflicts with existing letters.

        Args:
            clue: The Clue to place the word for.
            word: The proposed answer word.

        Returns:
            True if the word fits all current intersecting letters.
        """
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        for ch in word:
            cell = self.grid.grid[r][c]
            if cell.char and cell.char != ch:
                return False
            r += dr; c += dc
        return True

    def assign(self, clue: Clue, word: str) -> None:
        """
        Assign a chosen word to a clue and write letters into the grid.

        Args:
            clue: The Clue being assigned.
            word: The answer string to assign.
        """
        clue.assigned = word
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        for ch in word:
            self.grid.grid[r][c].char = ch
            r += dr; c += dc

    def propagate(self) -> bool:
        """
        Perform one pass of constraint propagation over all unassigned clues.

        If a clue has only one candidate or its top candidate fits cleanly,
        assign it. Repeat until no new assignments are made.

        Returns:
            True if any assignment was made, False otherwise.
        """
        progress = False
        for clue in list(self.grid.clues):
            if clue.assigned:
                continue
            candidates = self.fetch_candidates(clue)
            if not candidates:
                continue
            top_word, _ = candidates[0]
            if len(candidates) == 1 or self.fits_without_conflict(clue, top_word):
                self.assign(clue, top_word)
                progress = True
        return progress

    def solve(self) -> bool:
        """
        Solve the crossword via iterative propagation and backtracking.

        Returns:
            True if a solution is found, False otherwise.
        """
        while self.propagate():
            pass
        return self.backtrack()

    def backtrack(self) -> bool:
        """
        Recursive backtracking search over remaining unassigned clues.

        Uses MRV heuristic and state snapshots to explore assignments.

        Returns:
            True if a complete solution is found, False on dead end.
        """
        unassigned = [clue for clue in list(self.grid.clues) if not clue.assigned]
        if not unassigned:
            return True
        clue = min(unassigned, key=lambda c: len(self.fetch_candidates(c)))
        candidates = list(self.fetch_candidates(clue))
        # Save state
        grid_snapshot = [[cell.char for cell in row] for row in self.grid.grid]
        cache_snapshot = dict(self.cache)
        assigned_snapshot = [(c, c.assigned) for c in unassigned]

        for word, _ in candidates:
            if not self.fits_without_conflict(clue, word):
                continue
            self.assign(clue, word)
            while self.propagate():
                pass
            if self.backtrack():
                return True
            # restore state
            for r, row in enumerate(self.grid.grid):
                for c, cell in enumerate(row):
                    cell.char = grid_snapshot[r][c]
            self.cache = dict(cache_snapshot)
            for c, val in assigned_snapshot:
                c.assigned = val
        return False

# Example usage:
# grid = Grid(grid, clues)
# solver = CrosswordSolver(grid)
# solver.solve()
