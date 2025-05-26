from copy import deepcopy
from typing import Any

# Assuming Cell, Clue, and Grid are imported from entities.py
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
        self.backtrack_stack: list[tuple[Grid, list[Clue], dict[tuple[str, int], set[str]]]] = []
        self.tried_candidates: dict[tuple[str, int], set[str]] = {}

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
        raise NotImplementedError("Integrate with your answer-retrieval service here.")

    def current_pattern(self, clue: Clue) -> str:
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        pattern: list[str] = []
        r, c = clue.start
        for _ in range(clue.length):
            ch = self.grid.grid[r][c].char or '*'
            pattern.append(ch)
            r += dr; c += dc
        return ''.join(pattern)

    def fetch_candidates(self, clue: Clue) -> list[tuple[str, float]]:
        pattern = self.current_pattern(clue)
        key = (clue.direction, clue.number, pattern)
        if key not in self.cache:
            if clue.candidates:
                candidates = clue.candidates
            else:
                candidates = self.get_answers(clue.text, clue.length, pattern)
            candidates.sort(key=lambda x: x[1], reverse=True)
            self.cache[key] = candidates
        return self.cache[key]

    def fits_without_conflict(self, clue: Clue, word: str) -> bool:
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        for ch in word:
            cell = self.grid.grid[r][c]
            if cell.char and cell.char != ch:
                return False
            r += dr; c += dc
        return True

    def assign(self, clue: Clue, word: str) -> None:
        clue.assigned = word
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        for ch in word:
            self.grid.grid[r][c].char = ch
            r += dr; c += dc

    def unassign(self, clue: Clue) -> None:
        clue.assigned = None
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        for _ in range(clue.length):
            self.grid.grid[r][c].char = None
            r += dr; c += dc

    def grid_snapshot(self) -> list[str]:
        return [''.join('#' if cell.is_black else (cell.char if cell.char is not None else '*') for cell in row) for row in self.grid.grid]

    def solve_step(self) -> dict[str, object]:
        """
        Executes a single step of the crossword solving algorithm.

        This method attempts to assign the next most promising clue based on the highest-confidence
        untried candidate that fits without conflict. If no such assignment is possible, it backtracks
        to a previous state and retries a different path.

        Returns:
            A dictionary containing:
                - "progress" (bool): True if a change was made during this step.
                - "message" (str): A description of what action was taken (e.g., assignment or backtrack).
                - "solved" (bool): True if the puzzle has been completely and correctly solved.
        """
        self.unassigned_clues = [c for c in self.grid.clues if not c.assigned]
        if not self.unassigned_clues:
            return {"progress": False, "message": "Puzzle complete", "solved": True}

        def clue_best_confidence(clue: Clue) -> float:
            candidates = self.fetch_candidates(clue)
            valid: list[float] = [conf for word, conf in candidates if (clue.direction, clue.number) not in self.tried_candidates or word not in self.tried_candidates[(clue.direction, clue.number)]]
            return -max(valid) if valid else float('inf')

        self.unassigned_clues.sort(key=clue_best_confidence)
        for clue in self.unassigned_clues:
            clue_key = (clue.direction, clue.number)
            if clue_key not in self.tried_candidates:
                self.tried_candidates[clue_key] = set()

            candidates = self.fetch_candidates(clue)
            for word, _ in candidates:
                if word in self.tried_candidates[clue_key]:
                    continue

                self.tried_candidates[clue_key].add(word)  # Mark before snapshot

                if self.fits_without_conflict(clue, word):
                    snapshot = deepcopy(self.grid)
                    clue_snapshot = deepcopy([c for c in self.grid.clues])
                    tried_snapshot = deepcopy(self.tried_candidates)
                    self.backtrack_stack.append((snapshot, clue_snapshot, tried_snapshot))

                    self.assign(clue, word)
                    return {"progress": True, "message": f"Assigned '{word}' to {clue.direction} {clue.number}", "solved": False}

        if self.backtrack_stack:
            prev_grid, prev_clues, prev_tried = self.backtrack_stack.pop()
            self.grid = prev_grid
            self.grid.clues = prev_clues
            self.tried_candidates = prev_tried
            return {"progress": True, "message": "Backtracked to previous state", "solved": False}

        return {"progress": False, "message": "No valid assignments could be made", "solved": False}

    def solve(self, max_steps: int = 1000) -> dict[str, Any]:
        """
        Repeatedly call solve_step() until the puzzle is solved or no further progress can be made.
        Args:
            max_steps: Maximum number of steps to attempt (to prevent infinite loops).
        Returns:
            The final result dictionary from the last solve_step() call.
        """
        for _ in range(max_steps):
            result = self.solve_step()
            self.grid.print()
            print()
            if result.get('solved', False):
                return result
            if not result.get('progress', False):
                return result
        return {
            'progress': False,
            'message': f'Maximum steps ({max_steps}) reached. Puzzle not solved.',
            'solved': False
        }

    # def solve2(self) -> bool:
    #     while True:
    #         result = self.solve_step()
    #         print(result["message"])
    #         self.grid.print()
    #         if not result["progress"]:
    #             solved: bool = result["solved"]
    #             return solved
