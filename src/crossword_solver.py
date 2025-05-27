from copy import deepcopy

# Assuming Cell, Clue, and Grid are imported from entities.py
from .entities import Clue, Grid
from typing import cast, Any

class CrosswordSolver:
    def __init__(self, grid: Grid):
        self.grid = grid
        self.cache: dict[tuple[str, int, str], list[tuple[str, float]]] = {}
        self.unassigned_clues: list[Clue] = [c for c in self.grid.clues if not c.assigned]
        self.backtrack_stack: list[
            tuple[
                Grid,
                list[Clue],
                dict[tuple[str, int], set[str]],
                Clue,
                str
            ]
        ] = []        
        self.tried_candidates: dict[tuple[str, int], set[str]] = {}

    def get_serialized_grid_state(self) -> list[list[dict[str, Any]]]:
        return [
            [
                {
                    'char': cell.char,
                    'is_black': cell.is_black,
                    'across_id': cell.across_id,
                    'down_id': cell.down_id
                }
                for cell in row
            ]
            for row in self.grid.grid
        ]

    def get_answers(self, clue: str, length: int, known_letters: str) -> list[tuple[str, float]]:
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

    def restore_grid_state(self, dest_grid: Grid, src_grid: Grid):
        for r in range(len(src_grid.grid)):
            for c in range(len(src_grid.grid[r])):
                dest_grid.grid[r][c].char = src_grid.grid[r][c].char
        for dest_clue, src_clue in zip(dest_grid.clues, src_grid.clues):
            dest_clue.assigned = src_clue.assigned

    def solve_step(self) -> dict[str, object]:
        self.unassigned_clues = [c for c in self.grid.clues if not c.assigned]
        if not self.unassigned_clues:
            return {
                "progress": True,
                "solved": True,
                "message": "Puzzle complete",
                "assigned_clues": [],
                "grid": self.get_serialized_grid_state()
            }

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

                self.tried_candidates[clue_key].add(word)

                if self.fits_without_conflict(clue, word):
                    snapshot = deepcopy(self.grid)
                    clue_snapshot = deepcopy([c for c in self.grid.clues])
                    tried_snapshot = deepcopy(self.tried_candidates)
                    self.backtrack_stack.append((
                        snapshot, 
                        clue_snapshot, 
                        tried_snapshot, 
                        clue, 
                        word))

                    self.assign(clue, word)
                    return {
                        "progress": True, 
                        "solved": False,
                        "message": f"Assigned '{word}' to {clue.direction} {clue.number}", 
                        "assigned_clues": [{
                            "direction": clue.direction,
                            "number": clue.number,
                            "assigned": word
                        }],
                        "grid": self.get_serialized_grid_state()
                    }

        if self.backtrack_stack:
            prev_grid, prev_clues, prev_tried, last_clue, last_word = self.backtrack_stack.pop()
            self.grid = prev_grid
            self.grid.clues = prev_clues
            self.tried_candidates = prev_tried
            self.restore_grid_state(self.grid, prev_grid)
            return {
                "progress": True,
                "solved": False,
                "message": f"Backtracked: unassigned '{last_word}' from {last_clue.direction} {last_clue.number}",
                "assigned_clues": [{
                    "direction": last_clue.direction,
                    "number": last_clue.number,
                    "assigned": None
                }],
                "grid": self.get_serialized_grid_state()
            }

        return {
            "progress": False, 
            "solved": False, 
            "message": "No valid assignments could be made", 
            "assigned_clues": [],
            "grid": self.get_serialized_grid_state(),
        }

    def solve(self, max_steps: int = 1000) -> dict[str, object]:
        assigned_clues_total: list[dict[str, str | int]] = []
        for _ in range(max_steps):
            result = self.solve_step()
            self.grid.print()
            print()

            assigned_clues = cast(list[dict[str, str | int]], result.get("assigned_clues", []))
            assigned_clues_total.extend(assigned_clues)

            if result.get('solved', False):
                result["assigned_clues"] = assigned_clues_total
                return result
            if not result.get('progress', False):
                result["assigned_clues"] = assigned_clues_total
                return result
        return {
            'progress': False,
            'solved': False,
            'message': f'Maximum steps ({max_steps}) reached. Puzzle not solved.',
            'assigned_clues': assigned_clues_total,
            'grid': self.get_serialized_grid_state(),
        }
