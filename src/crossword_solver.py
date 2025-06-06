from copy import deepcopy
import requests
import hashlib

# Assuming Cell, Clue, and Grid are imported from entities.py
from .entities import Clue, Grid
from typing import cast, Any

class CrosswordSolver:
    def __init__(self, grid: Grid):
        self.grid = grid
        self.cache: dict[tuple[str, int, str], list[tuple[str, int]]] = {}
        self.unassigned_clues: list[Clue] = [c for c in self.grid.clues if not c.assigned]
        self.backtrack_stack: list[
            tuple[
                Grid,
                list[Clue],
                dict[tuple[str, int], set[tuple[str, str]]],
                Clue,
                str
            ]
        ] = []
        self.tried_candidates: dict[tuple[str, int], set[tuple[str, str]]] = {}
        self._prepopulated = grid.prepopulated

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

    def get_answers(self, clue: str, length: int, known_letters: str) -> list[tuple[str, int]]:
        """
        Query a local Ollama AI model for up to three candidate answers for the clue.
        Returns a list of (answer, confidence) tuples.
        """
        prompt = (
            "You are a crossword puzzle expert."
            "Provide up to three possible answers for each given clue.  Be optimistic and "
            "provide answers even if you are not sure about them.\n"
            "For each answer, assign a confidence score from 0 to 100 based on how likely it"
            "is correct — not just whether it fits.\n"
            "Answers may not include spaces or punctuation.\n"
            "Other than abbreviations or proper names, answers must be real English "
            "words or phrases.\n"
            "Do NOT make up words, or pad words with extra letters so they will fit.\n"
            "Do NOT provide any answer that does not fit the specified length.\n"
            "Your responses should be given in the following format: "
            "answer1:confidence1, answer2:confidence2, answer3:confidence3\n"
            "It is ESSENTIAL that you limit your response to this format.  Provide NO other"
            "commentary whatsoever."
            f"Clue: '{clue}'\n"
            f"Length: {length}\n"
            f"Known letters (* = unknown): {known_letters}\n"
            #"REPEAT: Do NOT provide any answers that do not fit the length or pattern. This is "
            #"the most important rule.\n"
        )
        try:
            print(f"[LLM QUERY] Clue: '{clue}' | Length: {length} | Pattern: {known_letters}")
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.1:8b",  # Change to your installed model name if needed
                    #"model": "gemma:27b",  # Change to your installed model name if needed
                    #"model": "phi4",  # Change to your installed model name if needed
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30  # Increased timeout to 30 seconds
            )
            response.raise_for_status()
            result = response.json()
            output = result.get("response", "")

            # Parse answers in the expected format
            candidates: list[tuple[str, int]] = []
            for part in output.split(","):
                part = part.strip()
                if ":" in part:
                    answer, conf = part.split(":", 1)
                    answer = answer.strip().upper()
                    try:
                        confidence = int(conf.strip())
                        confidence = max(0, min(confidence, 100))
                    except ValueError:
                        confidence = 50
                    if len(answer) == length:
                        candidates.append((answer, confidence))
                if len(candidates) == 3:
                    break
            # Debug print: show all candidates and their confidence levels
            print(f"[LLM RESPONSE] Candidates for clue '{clue}' (length {length}, pattern {known_letters}):")
            for answer, confidence in candidates:
                print(f"  {answer} ({confidence})")
            print()
            return candidates
        except Exception as e:
            print(f"Ollama query failed: {e}")
            return []

    def current_pattern(self, clue: Clue) -> str:
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        return ''.join(self.grid.grid[r + i * dr][c + i * dc].char or '*' for i in range(clue.length))

    def fetch_candidates(self, clue: Clue) -> list[tuple[str, int]]:
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

    def prepopulate_candidates(self, top_n: int = 3) -> None:
        for clue in self.grid.clues:
            pattern = '*' * clue.length  # empty pattern
            key = (clue.direction, clue.number, pattern)
            candidates = self.get_answers(clue.text, clue.length, pattern)
            candidates.sort(key=lambda x: x[1], reverse=True)
            self.cache[key] = candidates[:top_n]

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

    def grid_hash(self) -> str:
        flat = ''.join(''.join('#' if cell.is_black else (cell.char or '*') for cell in row) for row in self.grid.grid)
        return hashlib.md5(flat.encode()).hexdigest()

    def restore_grid_state(self, dest_grid: Grid, src_grid: Grid):
        for r in range(len(src_grid.grid)):
            for c in range(len(src_grid.grid[r])):
                dest_grid.grid[r][c].char = src_grid.grid[r][c].char
        for dest_clue, src_clue in zip(dest_grid.clues, src_grid.clues):
            dest_clue.assigned = src_clue.assigned

    def solve_step(self) -> dict[str, object]:
        if not self._prepopulated:
            self.prepopulate_candidates(top_n=3)
            self._prepopulated = True

        self.unassigned_clues = [c for c in self.grid.clues if not c.assigned]
        if not self.unassigned_clues:
            msg = "Puzzle complete"
            print(f"[SOLVE_STEP MESSAGE] {msg}")
            return {
                "progress": True,
                "solved": True,
                "message": msg,
                "assigned_clues": [],
                "grid": self.get_serialized_grid_state()
            }

        def clue_best_confidence(clue: Clue) -> int:
            candidates = self.fetch_candidates(clue)
            grid_key = self.grid_hash()
            valid = [conf for word, conf in candidates if (clue.direction, clue.number) not in self.tried_candidates or (word, grid_key) not in self.tried_candidates[(clue.direction, clue.number)]]
            return -max(valid) if valid else 101

        self.unassigned_clues.sort(key=clue_best_confidence)
        grid_key = self.grid_hash()

        for clue in self.unassigned_clues:
            clue_key = (clue.direction, clue.number)
            if clue_key not in self.tried_candidates:
                self.tried_candidates[clue_key] = set()

            candidates = self.fetch_candidates(clue)
            attempted: list[tuple[str, int]] = []
            grid_key = self.grid_hash()
            for word, confidence in candidates:
                if (word, grid_key) in self.tried_candidates[clue_key]:
                    continue
                attempted.append((word, confidence))
                self.tried_candidates[clue_key].add((word, grid_key))

                if self.fits_without_conflict(clue, word):
                    print(f"[TRY] {clue.direction} {clue.number}: Attempting '{word}' ({confidence}) ... SUCCESS")
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
                            "assigned": word,
                            "confidence": confidence
                        }],
                        "grid": self.get_serialized_grid_state()
                    }
                else:
                    print(f"[TRY] {clue.direction} {clue.number}: Attempting '{word}' ({confidence}) ... FAIL")
            if attempted:
                print(f"[TRY] {clue.direction} {clue.number}: All attempts failed: {[f'{w} ({c})' for w, c in attempted]}")
        if self.backtrack_stack:
            prev_grid, prev_clues, prev_tried, last_clue, last_word = self.backtrack_stack.pop()
            self.grid = prev_grid
            self.grid.clues = prev_clues
            self.tried_candidates = prev_tried
            self.restore_grid_state(self.grid, prev_grid)
            msg = f"Backtracked: unassigned '{last_word}' from {last_clue.direction} {last_clue.number}"
            print(f"[SOLVE_STEP MESSAGE] {msg}")
            return {
                "progress": True,
                "solved": False,
                "message": msg,
                "assigned_clues": [{
                    "direction": last_clue.direction,
                    "number": last_clue.number,
                    "assigned": None
                }],
                "grid": self.get_serialized_grid_state()
            }

        msg = "No valid assignments could be made"
        print(f"[SOLVE_STEP MESSAGE] {msg}")
        return {
            "progress": False,
            "solved": False,
            "message": msg,
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
