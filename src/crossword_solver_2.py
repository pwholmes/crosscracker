from .entities import Clue, Grid

class CrosswordSolver2:
    def __init__(self, grid: Grid):
        """
        Initializes the crossword solver with a Grid instance.

        Args:
            grid: The Grid instance containing cells and clues.
        """
        self.grid = grid
        self.cache: dict[tuple[str, int, str], list[tuple[str, float]]] = {}
        self.unassigned_clues: list[Clue] = [c for c in self.grid.clues if not c.assigned]

    # Placeholder for the real get_answers function
    def get_answers(self, clue: str, length: int, known_letters: str) -> list[tuple[str, float]]:
        """
        Retrieve potential answers for a given crossword clue.

        Args:
            clue: The text of the crossword clue.
            length: Expected length of the answer.
            known_letters: Pattern string with known letters and '*' for unknowns.

        Returns:
            A list of tuples (word, confidence) sorted by confidence descending.
        """
        #raise NotImplementedError("Integrate with your answer-retrieval service here.")
        return []

    def current_pattern(self, clue: Clue) -> str:
        """
        Build the current letter pattern for a clue from the grid.

        Unknown cells are represented by '*'.

        Args:
            clue: The Clue object to inspect.

        Returns:
            A string pattern of length clue.length.
        """
        dr, dc = (0, 1) if clue.direction == 'across' else (1, 0)
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

        Args:
            clue: The Clue object whose candidates to fetch.

        Returns:
            List of (word, confidence) tuples.
        """
        pattern = self.current_pattern(clue)
        key = (clue.direction, clue.number, pattern)
        if key not in self.cache:
            candidates = self.get_answers(clue.text, clue.length, pattern)
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
        dr, dc = (0, 1) if clue.direction == 'across' else (1, 0)
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
        dr, dc = (0, 1) if clue.direction == 'across' else (1, 0)
        r, c = clue.start
        for ch in word:
            self.grid.grid[r][c].char = ch
            r += dr; c += dc

    def grid_snapshot(self) -> list[str]:
        """
        Return a snapshot of the current grid as list of strings.

        Returns:
            List of strings representing each row in the grid.
        """
        return [''.join('#' if cell.is_black else (cell.char or '*') for cell in row) for row in self.grid.grid]

    def solve_step(self) -> tuple[bool, list[str], str]:
        """
        Perform a single solving step: choose and assign the best clue.

        Returns:
            A tuple: (progress_made, current_grid_snapshot, description_message)
        """
        self.unassigned_clues = [c for c in self.grid.clues if not c.assigned]
        if not self.unassigned_clues:
            return False, self.grid_snapshot(), "Puzzle complete"

        def clue_best_confidence(clue: Clue) -> float:
            candidates = self.fetch_candidates(clue)
            valid: list[float] = [conf for _, conf in candidates]
            return -max(valid) if valid else float('inf')

        self.unassigned_clues.sort(key=clue_best_confidence)
        for clue in self.unassigned_clues:
            candidates = self.fetch_candidates(clue)
            for word, _ in candidates:
                if self.fits_without_conflict(clue, word):
                    self.assign(clue, word)
                    return True, self.grid_snapshot(), f"Assigned '{word}' to {clue.direction} {clue.number}"
        return False, self.grid_snapshot(), "No valid assignments could be made"

    def solve(self) -> bool:
        """
        Iteratively solve the crossword puzzle without recursion.

        Returns:
            True if solved, False otherwise.
        """
        while True:
            progress, _, message = self.solve_step()
            print(message)
            if not progress:
                return all(c.assigned for c in self.grid.clues)
