from flask import Flask, render_template, jsonify
from typing import List, Dict, Any, Optional, Set
from src.crossword_solver import CrosswordSolver, Clue, Grid
# Import test data from data.test_data
from data.test_data import EMPTY_TEST_GRID, TEST_CLUES

app = Flask(__name__)

# Global variables to store the solver state
solver: Optional[CrosswordSolver] = None
grid: Optional[Grid] = None
solving_thread = None
solution_steps: List[Dict[str, Any]] = []
assignment_order: List[Clue] = []  # Track the order in which clues are assigned

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initialize', methods=['POST'])
def initialize_puzzle():
    global solver, grid, solution_steps, tried_candidates, exhausted_clues, failed_combinations, assignment_order
    
    # Reset solution steps and tracking variables
    solution_steps = []
    tried_candidates = {}  # Reset to empty dictionary
    exhausted_clues = set()
    failed_combinations = {}  # Reset failed combinations
    assignment_order = []  # Reset assignment order
    
    # Create fresh copies of the test clues with assigned=None
    fresh_clues: List[Clue] = []
    for clue in TEST_CLUES:
        fresh_clue = Clue(
            clue.number,
            clue.direction,
            clue.text,
            clue.length,
            clue.start[0],
            clue.start[1],
            clue.candidates.copy() if clue.candidates else []
        )
        fresh_clues.append(fresh_clue)
    
    # Create grid and solver with fresh clues
    grid = Grid(EMPTY_TEST_GRID, fresh_clues)
    solver = CrosswordSolver(grid)
    
    # Get initial grid state
    grid_state: List[List[Dict[str, Any]]] = []
    for row in grid.grid:
        grid_row: List[Dict[str, Any]] = []
        for cell in row:
            grid_row.append({
                'char': grid.display_cell_char(cell),
                'is_black': cell.is_black,
                'across_id': cell.across_id,
                'down_id': cell.down_id
            })
        grid_state.append(grid_row)
    
    # Get clues
    across_clues: List[Dict[str, Any]] = []
    down_clues: List[Dict[str, Any]] = []
    for clue in grid.clues:
        clue_data: Dict[str, Any] = {
            'number': clue.number,
            'text': clue.text,
            'length': clue.length,
            'start': clue.start,
            'assigned': clue.assigned
        }
        if clue.direction == 'A':
            across_clues.append(clue_data)
        else:
            down_clues.append(clue_data)
    
    return jsonify({
        'grid': grid_state,
        'across_clues': across_clues,
        'down_clues': down_clues
    })

# Keep track of tried candidates for each clue in each context
# The structure is: {clue_key: {context: [tried_candidates]}}
# where context is a string representation of the current assignment state
tried_candidates: Dict[str, Dict[str, List[str]]] = {}
exhausted_clues: Set[str] = set()  # Clues for which all candidates have been tried

# Track failed combinations to avoid infinite loops
# The structure is: {context: Set[str]}
# where context is a string representation of the current assignment state
# and the set contains clue keys that have been tried and failed in this context
failed_combinations: Dict[str, Set[str]] = {}

def get_context(grid: Grid) -> str:
    """Generate a string representation of the current grid state to use as context."""
    context_items: List[str] = []
    for clue in grid.clues:
        if clue.assigned:
            context_items.append(f"{clue.number}{clue.direction}:{clue.assigned}")
    return ",".join(sorted(context_items))

@app.route('/api/solve_step', methods=['GET'])
def solve_step():
    global solver, grid, solution_steps, tried_candidates, exhausted_clues, failed_combinations, assignment_order
    
    if solver is None or grid is None:
        return jsonify({'error': 'Solver not initialized'}), 400
    
    # Find an unassigned clue with the fewest candidates
    unassigned_clues = [clue for clue in grid.clues if not clue.assigned]
    print(f"Unassigned clues: {len(unassigned_clues)}")
    
    if not unassigned_clues:
        return jsonify({
            'grid': get_grid_state(grid),
            'assigned_clues': get_assigned_clues(grid),
            'progress': False,
            'message': 'All clues are already assigned.'
        })
    
    # Sort by number of candidates (MRV heuristic)
    # We already checked that solver is not None above
    assert solver is not None  # Tell type checker that solver is not None
    
    # Define a helper function to get the highest confidence level of a clue's candidates
    def get_highest_confidence(clue: Clue) -> float:
        if solver is None:
            return float('-inf')
        candidates = solver.fetch_candidates(clue)
        if not candidates:
            return float('-inf')
        # Return negative of highest confidence so that higher confidence comes first when minimizing
        return -max(confidence for _, confidence in candidates)
    
    # Get the current context
    current_context = get_context(grid)
    
    # Check if we have any failed combinations for this context
    if current_context in failed_combinations:
        # Filter out clues that have already failed in this context
        valid_clues = [clue for clue in unassigned_clues 
                      if f"{clue.number}{clue.direction}" not in failed_combinations[current_context]]
        
        # If all clues have failed in this context, we need to backtrack
        if not valid_clues:
            # We need to backtrack to a different context
            if not assignment_order:
                return jsonify({
                    'grid': get_grid_state(grid),
                    'assigned_clues': get_assigned_clues(grid),
                    'progress': False,
                    'message': 'All possible combinations have been tried. No solution found.'
                })
            
            # Get the last assigned clue from our assignment order
            last_clue = assignment_order.pop()
            clue_key = f"{last_clue.number}{last_clue.direction}"
            
            # Unassign it
            print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
            last_assigned = last_clue.assigned
            last_clue.assigned = None
            
            # Clear the grid cells for this clue, but only if they're not used by other assigned clues
            dr, dc = (0, 1) if last_clue.direction == 'A' else (1, 0)
            r, c = last_clue.start
            for i in range(last_clue.length):
                current_r, current_c = r + i * dr, c + i * dc
                cell = grid.grid[current_r][current_c]
                
                # Check if this cell is used by any other assigned clue
                used_by_other_clue = False
                for other_clue in grid.clues:
                    if other_clue.assigned and other_clue != last_clue:
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
            
            # Add this word to tried candidates for this clue in the current context
            if clue_key not in tried_candidates:
                tried_candidates[clue_key] = {}
            if current_context not in tried_candidates[clue_key]:
                tried_candidates[clue_key][current_context] = []
            if last_assigned is not None:
                tried_candidates[clue_key][current_context].append(last_assigned)
            
            # Clear failed combinations for this context
            if current_context in failed_combinations:
                del failed_combinations[current_context]
            
            # Reset the exhausted status
            exhausted_clues.clear()
            
            return jsonify({
                'grid': get_grid_state(grid),
                'assigned_clues': get_assigned_clues(grid),
                'progress': True,
                'message': f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.'
            })
        
        # Use the valid clues
        unassigned_clues = valid_clues
    
    clue_to_solve = min(unassigned_clues, key=get_highest_confidence)
    candidates = solver.fetch_candidates(clue_to_solve)
    print(f"Selected clue: {clue_to_solve.number} {clue_to_solve.direction}, candidates: {candidates}")
    
    if not candidates:
        # If we have no candidates for this clue, we need to backtrack
        # Find the most recently assigned clue and try its next candidate
        if not assignment_order:
            return jsonify({
                'grid': get_grid_state(grid),
                'assigned_clues': get_assigned_clues(grid),
                'progress': False,
                'message': 'No candidates available and no previous assignments to backtrack to.'
            })
        
        # Get the last assigned clue from our assignment order
        last_clue = assignment_order.pop()
        clue_key = f"{last_clue.number}{last_clue.direction}"
        
        # Unassign it
        print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
        last_assigned = last_clue.assigned
        last_clue.assigned = None
        
        # Clear the grid cells for this clue, but only if they're not used by other assigned clues
        dr, dc = (0, 1) if last_clue.direction == 'A' else (1, 0)
        r, c = last_clue.start
        for i in range(last_clue.length):
            current_r, current_c = r + i * dr, c + i * dc
            cell = grid.grid[current_r][current_c]
            
            # Check if this cell is used by any other assigned clue
            used_by_other_clue = False
            for other_clue in grid.clues:
                if other_clue.assigned and other_clue != last_clue:
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
        
        # Add this word to tried candidates for this clue in the current context
        current_context = get_context(grid)
        if clue_key not in tried_candidates:
            tried_candidates[clue_key] = {}
        if current_context not in tried_candidates[clue_key]:
            tried_candidates[clue_key][current_context] = []
        if last_assigned is not None:
            tried_candidates[clue_key][current_context].append(last_assigned)
            
        # When we backtrack to a clue, we need to clear the tried_candidates for all clues that come after it
        # This is because we're starting a new branch of the search tree
        clues_to_clear: List[str] = []
        for c in grid.clues:
            c_key = f"{c.number}{c.direction}"
            # If this clue comes after the one we're backtracking to, clear its tried candidates
            if c.number > last_clue.number or (c.number == last_clue.number and c.direction > last_clue.direction):
                clues_to_clear.append(c_key)
        
        # Clear tried candidates for clues that come after the one we're backtracking to
        for c_key in clues_to_clear:
            if c_key in tried_candidates:
                tried_candidates[c_key] = {}
            
        # Reset the exhausted status
        exhausted_clues.clear()
        
        # DO NOT clear the tried candidates for this clue in the current branch
        # We only want to clear tried candidates when we backtrack to a different branch
        
        return jsonify({
            'grid': get_grid_state(grid),
            'assigned_clues': get_assigned_clues(grid),
            'progress': True,
            'message': f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.'
        })
    
    # Get the clue key and current context for tracking tried candidates
    clue_key = f"{clue_to_solve.number}{clue_to_solve.direction}"
    current_context = get_context(grid)
    
    # Initialize the dictionary for this clue if it doesn't exist
    if clue_key not in tried_candidates:
        tried_candidates[clue_key] = {}
    
    # Initialize the list for this context if it doesn't exist
    if current_context not in tried_candidates[clue_key]:
        tried_candidates[clue_key][current_context] = []
    
    # Check if we've already tried all candidates for this clue in the current context
    untried_candidates = [word for word, _ in candidates if word not in tried_candidates[clue_key][current_context]]
    if not untried_candidates:
        # All candidates for this clue have been tried, mark it as exhausted
        exhausted_clues.add(clue_key)
        
        # Check if we've exhausted all possibilities
        all_clues_exhausted = True
        for clue in grid.clues:
            clue_key_check = f"{clue.number}{clue.direction}"
            if clue_key_check not in exhausted_clues:
                all_clues_exhausted = False
                break
        
        if all_clues_exhausted:
            return jsonify({
                'grid': get_grid_state(grid),
                'assigned_clues': get_assigned_clues(grid),
                'progress': False,
                'message': 'All possible combinations have been tried. No solution found.'
            })
        
        # We need to backtrack
        if not assignment_order:
            return jsonify({
                'grid': get_grid_state(grid),
                'assigned_clues': get_assigned_clues(grid),
                'progress': False,
                'message': 'All candidates tried and no previous assignments to backtrack to.'
            })
        
        # Get the last assigned clue from our assignment order
        last_clue = assignment_order.pop()
        clue_key = f"{last_clue.number}{last_clue.direction}"
        
        # Unassign it
        print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
        last_assigned = last_clue.assigned
        last_clue.assigned = None
        
        # Clear the grid cells for this clue, but only if they're not used by other assigned clues
        dr, dc = (0, 1) if last_clue.direction == 'A' else (1, 0)
        r, c = last_clue.start
        for i in range(last_clue.length):
            current_r, current_c = r + i * dr, c + i * dc
            cell = grid.grid[current_r][current_c]
            
            # Check if this cell is used by any other assigned clue
            used_by_other_clue = False
            for other_clue in grid.clues:
                if other_clue.assigned and other_clue != last_clue:
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
        
        # Add this word to tried candidates for this clue in the current context
        current_context = get_context(grid)
        if clue_key not in tried_candidates:
            tried_candidates[clue_key] = {}
        if current_context not in tried_candidates[clue_key]:
            tried_candidates[clue_key][current_context] = []
        if last_assigned is not None:
            tried_candidates[clue_key][current_context].append(last_assigned)
        
        # Reset the exhausted status for this clue and any clues that might depend on it
        # This is important to ensure we don't get stuck in an infinite loop
        exhausted_clues.clear()  # Reset all exhausted clues when backtracking
        
        # DO NOT clear the tried candidates for this clue in the current branch
        # We only want to clear tried candidates when we backtrack to a different branch
        
        progress = True
        message = f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.'
        
        return jsonify({
            'grid': get_grid_state(grid),
            'assigned_clues': get_assigned_clues(grid),
            'progress': progress,
            'message': message
        })
    
    # Try each candidate that hasn't been tried yet
    for word, confidence in candidates:
        if word in tried_candidates[clue_key][current_context]:
            continue  # Skip already tried candidates
            
        fits = solver.fits_without_conflict(clue_to_solve, word)
        print(f"Trying word: {word} (confidence: {confidence}), fits without conflict: {fits}")
        
        if fits:
            solver.assign(clue_to_solve, word)
            # Add this clue to the assignment order
            assignment_order.append(clue_to_solve)
            progress = True
            message = f'Assigned "{word}" to {clue_to_solve.number} {clue_to_solve.direction}.'
            break
        else:
            # Add to tried candidates for this clue in the current context
            tried_candidates[clue_key][current_context].append(word)
    else:
        # If we've tried all candidates for this clue in this context, mark it as exhausted
        exhausted_clues.add(clue_key)
        
        # Mark this clue as failed in the current context
        # This will help us avoid trying this clue again in the same context
        if current_context not in failed_combinations:
            failed_combinations[current_context] = set()
        failed_combinations[current_context].add(clue_key)
        print(f"Marked clue {clue_key} as failed in context {current_context}")
        
        # If we've tried all candidates and none fit, we need to backtrack
        # This is similar to the no candidates case above
        if not assignment_order:
            return jsonify({
                'grid': get_grid_state(grid),
                'assigned_clues': get_assigned_clues(grid),
                'progress': False,
                'message': 'All candidates tried and no previous assignments to backtrack to.'
            })
        
        # Get the last assigned clue from our assignment order
        last_clue = assignment_order.pop()
        clue_key = f"{last_clue.number}{last_clue.direction}"
        
        # Unassign it
        print(f"Backtracking: unassigning {last_clue.number} {last_clue.direction}: {last_clue.assigned}")
        last_assigned = last_clue.assigned
        last_clue.assigned = None
        
        # Clear the grid cells for this clue, but only if they're not used by other assigned clues
        dr, dc = (0, 1) if last_clue.direction == 'A' else (1, 0)
        r, c = last_clue.start
        for i in range(last_clue.length):
            current_r, current_c = r + i * dr, c + i * dc
            cell = grid.grid[current_r][current_c]
            
            # Check if this cell is used by any other assigned clue
            used_by_other_clue = False
            for other_clue in grid.clues:
                if other_clue.assigned and other_clue != last_clue:
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
        
        # Add this word to tried candidates for this clue in the current context
        current_context = get_context(grid)
        if clue_key not in tried_candidates:
            tried_candidates[clue_key] = {}
        if current_context not in tried_candidates[clue_key]:
            tried_candidates[clue_key][current_context] = []
        if last_assigned is not None:
            tried_candidates[clue_key][current_context].append(last_assigned)
            
        # When we backtrack to a clue, we need to clear the tried_candidates for all clues that come after it
        # This is because we're starting a new branch of the search tree
        clues_to_clear: List[str] = []
        for c in grid.clues:
            c_key = f"{c.number}{c.direction}"
            # If this clue comes after the one we're backtracking to, clear its tried candidates
            if c.number > last_clue.number or (c.number == last_clue.number and c.direction > last_clue.direction):
                clues_to_clear.append(c_key)
        
        # Clear tried candidates for clues that come after the one we're backtracking to
        for c_key in clues_to_clear:
            if c_key in tried_candidates:
                tried_candidates[c_key] = {}
        
        progress = True
        message = f'Backtracked: unassigned "{last_assigned}" from {last_clue.number} {last_clue.direction}.'
    
    # Debug: Print grid state after assignment
    print("Grid state after assignment:")
    if grid:
        grid.print()
    
    # Get grid state and assigned clues for response
    grid_state = get_grid_state(grid)
    assigned_clues = get_assigned_clues(grid)
    print(f"Assigned clues: {len(assigned_clues)}")
    
    # Check if all clues are assigned
    all_assigned = len(unassigned_clues) == 0
    is_correct = True  # If all clues are assigned, the solution is valid
    if all_assigned:
        message = 'Puzzle solved correctly!'
    
    return jsonify({
        'grid': grid_state,
        'assigned_clues': assigned_clues,
        'progress': progress,
        'message': message,
        'is_correct': is_correct
    })

def get_grid_state(grid: Grid) -> List[List[Dict[str, Any]]]:
    """Helper function to get the current grid state."""
    grid_state: List[List[Dict[str, Any]]] = []
    for row in grid.grid:
        grid_row: List[Dict[str, Any]] = []
        for cell in row:
            grid_row.append({
                'char': grid.display_cell_char(cell),
                'is_black': cell.is_black,
                'across_id': cell.across_id,
                'down_id': cell.down_id
            })
        grid_state.append(grid_row)
    return grid_state

def get_assigned_clues(grid: Grid) -> List[Dict[str, Any]]:
    """Helper function to get the assigned clues."""
    assigned_clues: List[Dict[str, Any]] = []
    for clue in grid.clues:
        if clue.assigned:
            assigned_clues.append({
                'number': clue.number,
                'direction': clue.direction,
                'text': clue.text,
                'assigned': clue.assigned
            })
    return assigned_clues

def is_grid_correct(grid: Grid) -> bool:
    """Check if the current grid solution is valid."""
    # Check if all clues are assigned
    if not all(clue.assigned for clue in grid.clues):
        return False
    
    # Check if there are any conflicts in the grid
    for clue in grid.clues:
        if not clue.assigned:
            continue
        
        # Check if the assigned word fits in the grid without conflicts
        r, c = clue.start
        dr, dc = (0, 1) if clue.direction == 'A' else (1, 0)
        
        for i, char in enumerate(clue.assigned):
            cell = grid.grid[r + i * dr][c + i * dc]
            if cell.char != char:
                return False
    
    return True

@app.route('/api/solve_all', methods=['GET'])
def solve_all():
    global solver, grid
    
    if solver is None or grid is None:
        return jsonify({'error': 'Solver not initialized'}), 400
    
    # Solve the puzzle
    solver.solve()
    
    # Get final grid state
    grid_state = get_grid_state(grid)
    assigned_clues = get_assigned_clues(grid)
    
    # If all clues are assigned, the solution is valid
    is_correct = True
    message = 'Puzzle solved correctly!'
    
    return jsonify({
        'grid': grid_state,
        'assigned_clues': assigned_clues,
        'is_correct': is_correct,
        'message': message
    })

if __name__ == '__main__':
    app.run(debug=True)
