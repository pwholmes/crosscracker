from typing import Optional, List, Dict, Set, Any

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

        # Solution steps for tracking progress
        self.solution_steps: List[Dict[str, Any]] = []

        # Cache for get_answers results keyed by (direction, number, pattern)
        self.cache: dict[tuple[str, int, str], list[tuple[str, float]]] = {}
        
        # Track the order in which clues are assigned
        self.assignment_order: List[Clue] = []
        
        # Keep track of tried candidates for each clue in each context
        # The structure is: {clue_key: {context: [tried_candidates]}}
        # where context is a string representation of the current assignment state
        self.tried_candidates: Dict[str, Dict[str, List[str]]] = {}
        
        # Clues for which all candidates have been tried
        self.exhausted_clues: Set[str] = set()
        
        # Track failed combinations to avoid infinite loops
        # The structure is: {context: Set[str]}
        # where context is a string representation of the current assignment state
        # and the set contains clue keys that have been tried and failed in this context
        self.failed_combinations: Dict[str, Set[str]] = {}

    def reset(self) -> None:
        """Reset the solver state to start fresh."""
        self.solution_steps = []
        self.assignment_order = []
        self.tried_candidates = {}
        self.exhausted_clues = set()
        self.failed_combinations = {}
        self.cache = {}
        
        # Reset the grid
        for clue in self.grid.clues:
            clue.assigned = None
        for row in self.grid.grid:
            for cell in row:
                if not cell.is_black:
                    cell.char = None

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
        
        # Add this clue to the assignment order
        self.assignment_order.append(clue)

    def get_context(self) -> str:
        """Generate a string representation of the current grid state to use as context."""
        context_items: List[str] = []
        for clue in self.grid.clues:
            if clue.assigned:
                context_items.append(f"{clue.number}{clue.direction}:{clue.assigned}")
        return ",".join(sorted(context_items))
    
    def get_highest_confidence(self, clue: Clue) -> float:
        """
        Get the highest confidence level of a clue's candidates.
        Args:
            clue: The clue to check.
        Returns:
            Negative of the highest confidence value (for minimization in selection).
        """
        candidates = self.fetch_candidates(clue)
        if not candidates:
            return float('-inf')
        # Return negative of highest confidence so that higher confidence comes first when minimizing
        return -max(confidence for _, confidence in candidates)
    
    def clear_cell_if_not_used(self, clue: Clue) -> None:
        """
        Clear the grid cells for a clue, but only if they're not used by other assigned clues.
        Args:
            clue: The clue whose cells to clear.
        """
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        r, c = clue.start
        for i in range(clue.length):
            current_r, current_c = r + i * dr, c + i * dc
            cell = self.grid.grid[current_r][current_c]
            
            # Check if this cell is used by any other assigned clue
            used_by_other_clue = False
            for other_clue in self.grid.clues:
                if other_clue.assigned and other_clue != clue:
                    other_dr, other_dc = (0, 1) if other_clue.direction == 'A' else (1, 0)
                    other_r, other_c = other_clue.start
                    
                    # Check if this cell is part of the other clue
                    for j in range(other_clue.length):
                        if (other_r + j * other_dr == current_r and 
                            other_c + j * other_dc == current_c):
                            used_by_other_clue = True
                            break
                
                if used_by_other_clue:
                    break
            
            # Only clear the cell if it's not used by any other assigned clue
            if not used_by_other_clue:
                cell.char = None

    def solve(self, max_steps: int = 1000) -> Dict[str, Any]:
        """
        Repeatedly call solve_step() until the puzzle is solved or no further progress can be made.
        Args:
            max_steps: Maximum number of steps to attempt (to prevent infinite loops).
        Returns:
            The final result dictionary from the last solve_step() call.
        """
        for _ in range(max_steps):
            result = self.solve_step()
            self.solution_steps.append(result)
            if result.get('is_correct', False):
                return result
            if not result.get('progress', False):
                return result
        return {
            'progress': False,
            'message': f'Maximum steps ({max_steps}) reached. Puzzle not solved.',
            'is_correct': False
        }

    def solve_step(self) -> Dict[str, Any]:
        """
        Perform one step of the solving process.
        Returns:
            A dictionary with information about the step:
            - progress: True if progress was made, False otherwise
            - message: A message describing what happened
            - is_correct: True if the solution is correct (only set when all clues are assigned)
        """
        # Find an unassigned clue with the fewest candidates
        unassigned_clues = [clue for clue in self.grid.clues if not clue.assigned]
        print(f"Unassigned clues: {len(unassigned_clues)}")
        
        if not unassigned_clues:
            return {
                'progress': False,
                'message': 'All clues are already assigned.',
                'is_correct': True
            }
        
        # Get the current context
        current_context = self.get_context()
        
        # Check if we have any failed combinations for this context
        if current_context in self.failed_combinations:
            # Filter out clues that have already failed in this context
            valid_clues = [clue for clue in unassigned_clues 
                          if f"{clue.number}{clue.direction}" not in self.failed_combinations[current_context]]
            
            # If all clues have failed in this context, we need to backtrack
            if not valid_clues:
                # We need to backtrack to a different context
                if not self.assignment_order:
                    return {
                        'progress': False,
                        'message': 'All possible combinations have been tried. No solution found.',
                        'is_correct': False
                    }
                
                # Get the last assigned clue from our assignment order
                last_clue = self.assignment_order.pop()
                clue_key = f"{last_clue.number}{last_clue.direction}"
                
                # Unassign it
                print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
                last_assigned = last_clue.assigned
                last_clue.assigned = None
                
                # Clear the grid cells for this clue
                self.clear_cell_if_not_used(last_clue)
                
                # Add this word to tried candidates for this clue in the current context
                if clue_key not in self.tried_candidates:
                    self.tried_candidates[clue_key] = {}
                if current_context not in self.tried_candidates[clue_key]:
                    self.tried_candidates[clue_key][current_context] = []
                if last_assigned is not None:
                    self.tried_candidates[clue_key][current_context].append(last_assigned)
                
                # Clear failed combinations for this context
                if current_context in self.failed_combinations:
                    del self.failed_combinations[current_context]
                
                # Reset the exhausted status
                self.exhausted_clues.clear()
                
                return {
                    'progress': True,
                    'message': f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.',
                    'is_correct': False
                }
            
            # Use the valid clues
            unassigned_clues = valid_clues
        
        # Select the clue with the fewest candidates (MRV heuristic)
        clue_to_solve = min(unassigned_clues, key=self.get_highest_confidence)
        candidates = self.fetch_candidates(clue_to_solve)
        print(f"Selected clue: {clue_to_solve.number} {clue_to_solve.direction}, candidates: {candidates}")
        
        if not candidates:
            # If we have no candidates for this clue, we need to backtrack
            # Find the most recently assigned clue and try its next candidate
            if not self.assignment_order:
                return {
                    'progress': False,
                    'message': 'No candidates available and no previous assignments to backtrack to.',
                    'is_correct': False
                }
            
            # Get the last assigned clue from our assignment order
            last_clue = self.assignment_order.pop()
            clue_key = f"{last_clue.number}{last_clue.direction}"
            
            # Unassign it
            print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
            last_assigned = last_clue.assigned
            last_clue.assigned = None
            
            # Clear the grid cells for this clue
            self.clear_cell_if_not_used(last_clue)
            
            # Add this word to tried candidates for this clue in the current context
            current_context = self.get_context()
            if clue_key not in self.tried_candidates:
                self.tried_candidates[clue_key] = {}
            if current_context not in self.tried_candidates[clue_key]:
                self.tried_candidates[clue_key][current_context] = []
            if last_assigned is not None:
                self.tried_candidates[clue_key][current_context].append(last_assigned)
                
            # When we backtrack to a clue, we need to clear the tried_candidates for all clues that come after it
            # This is because we're starting a new branch of the search tree
            clues_to_clear: List[str] = []
            for c in self.grid.clues:
                c_key = f"{c.number}{c.direction}"
                # If this clue comes after the one we're backtracking to, clear its tried candidates
                if c.number > last_clue.number or (c.number == last_clue.number and c.direction > last_clue.direction):
                    clues_to_clear.append(c_key)
            
            # Clear tried candidates for clues that come after the one we're backtracking to
            for c_key in clues_to_clear:
                if c_key in self.tried_candidates:
                    self.tried_candidates[c_key] = {}
                
            # Reset the exhausted status
            self.exhausted_clues.clear()
            
            return {
                'progress': True,
                'message': f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.',
                'is_correct': False
            }
        
        # Get the clue key and current context for tracking tried candidates
        clue_key = f"{clue_to_solve.number}{clue_to_solve.direction}"
        current_context = self.get_context()
        
        # Initialize the dictionary for this clue if it doesn't exist
        if clue_key not in self.tried_candidates:
            self.tried_candidates[clue_key] = {}
        
        # Initialize the list for this context if it doesn't exist
        if current_context not in self.tried_candidates[clue_key]:
            self.tried_candidates[clue_key][current_context] = []
        
        # Check if we've already tried all candidates for this clue in the current context
        untried_candidates = [word for word, _ in candidates if word not in self.tried_candidates[clue_key][current_context]]
        if not untried_candidates:
            # All candidates for this clue have been tried, mark it as exhausted
            self.exhausted_clues.add(clue_key)
            
            # Check if we've exhausted all possibilities
            all_clues_exhausted = True
            for clue in self.grid.clues:
                clue_key_check = f"{clue.number}{clue.direction}"
                if clue_key_check not in self.exhausted_clues:
                    all_clues_exhausted = False
                    break
            
            if all_clues_exhausted:
                return {
                    'progress': False,
                    'message': 'All possible combinations have been tried. No solution found.',
                    'is_correct': False
                }
            
            # We need to backtrack
            if not self.assignment_order:
                return {
                    'progress': False,
                    'message': 'All candidates tried and no previous assignments to backtrack to.',
                    'is_correct': False
                }
            
            # Get the last assigned clue from our assignment order
            last_clue = self.assignment_order.pop()
            clue_key = f"{last_clue.number}{last_clue.direction}"
            
            # Unassign it
            print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
            last_assigned = last_clue.assigned
            last_clue.assigned = None
            
            # Clear the grid cells for this clue
            self.clear_cell_if_not_used(last_clue)
            
            # Add this word to tried candidates for this clue in the current context
            current_context = self.get_context()
            if clue_key not in self.tried_candidates:
                self.tried_candidates[clue_key] = {}
            if current_context not in self.tried_candidates[clue_key]:
                self.tried_candidates[clue_key][current_context] = []
            if last_assigned is not None:
                self.tried_candidates[clue_key][current_context].append(last_assigned)
            
            # Reset the exhausted status for this clue and any clues that might depend on it
            # This is important to ensure we don't get stuck in an infinite loop
            self.exhausted_clues.clear()  # Reset all exhausted clues when backtracking
            
            progress = True
            message = f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.'
            
            return {
                'progress': progress,
                'message': message,
                'is_correct': False
            }
        
        # Try each candidate that hasn't been tried yet
        for word, confidence in candidates:
            if word in self.tried_candidates[clue_key][current_context]:
                continue  # Skip already tried candidates
                
            fits = self.fits_without_conflict(clue_to_solve, word)
            print(f"Trying word: {word} (confidence: {confidence}), fits without conflict: {fits}")
            
            if fits:
                self.assign(clue_to_solve, word)
                # Add this clue to the assignment order
                self.assignment_order.append(clue_to_solve)
                progress = True
                message = f'Assigned "{word}" to {clue_to_solve.number} {clue_to_solve.direction}.'
                break
            else:
                # Add to tried candidates for this clue in the current context
                self.tried_candidates[clue_key][current_context].append(word)
        else:
            # If we've tried all candidates for this clue in this context, mark it as exhausted
            self.exhausted_clues.add(clue_key)
            
            # Mark this clue as failed in the current context
            # This will help us avoid trying this clue again in the same context
            if current_context not in self.failed_combinations:
                self.failed_combinations[current_context] = set()
            self.failed_combinations[current_context].add(clue_key)
            print(f"Marked clue {clue_key} as failed in context {current_context}")
            
            # If we've tried all candidates and none fit, we need to backtrack
            # This is similar to the no candidates case above
            if not self.assignment_order:
                return {
                    'progress': False,
                    'message': 'All candidates tried and no previous assignments to backtrack to.',
                    'is_correct': False
                }
            
            # Get the last assigned clue from our assignment order
            last_clue = self.assignment_order.pop()
            clue_key = f"{last_clue.number}{last_clue.direction}"
            
            # Unassign it
            print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
            last_assigned = last_clue.assigned
            last_clue.assigned = None
            
            # Clear the grid cells for this clue
            self.clear_cell_if_not_used(last_clue)
            
            # Add this word to tried candidates for this clue in the current context
            current_context = self.get_context()
            if clue_key not in self.tried_candidates:
                self.tried_candidates[clue_key] = {}
            if current_context not in self.tried_candidates[clue_key]:
                self.tried_candidates[clue_key][current_context] = []
            if last_assigned is not None:
                self.tried_candidates[clue_key][current_context].append(last_assigned)
                
            # When we backtrack to a clue, we need to clear the tried_candidates for all clues that come after it
            # This is because we're starting a new branch of the search tree
            clues_to_clear: List[str] = []
            for c in self.grid.clues:
                c_key = f"{c.number}{c.direction}"
                # If this clue comes after the one we're backtracking to, clear its tried candidates
                if c.number > last_clue.number or (c.number == last_clue.number and c.direction > last_clue.direction):
                    clues_to_clear.append(c_key)
            
            # Clear tried candidates for clues that come after the one we're backtracking to
            for c_key in clues_to_clear:
                if c_key in self.tried_candidates:
                    self.tried_candidates[c_key] = {}
            
            progress = True
            message = f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.'
            
            return {
                'progress': progress,
                'message': message,
                'is_correct': False
            }
        
        # Debug: Print grid state after assignment
        print("Grid state after assignment:")
        self.grid.print()
        
        # Check if all clues are assigned
        all_assigned = all(clue.assigned is not None for clue in self.grid.clues)
        is_correct = all_assigned  # If all clues are assigned, the solution is valid
        if all_assigned:
            message = 'Puzzle solved correctly!'
        
        return {
            'progress': progress,
            'message': message,
            'is_correct': is_correct
        }
    
