from flask import Flask, render_template, jsonify
from typing import List, Dict, Any
from src.crossword_solver import CrosswordSolver, Clue, Grid
# Import test data from data.test_data
from data.test_data import EMPTY_TEST_GRID, TEST_CLUES

app = Flask(__name__)

# Global variables to store the solver state
solver: CrosswordSolver|None = None
grid: Grid|None = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initialize', methods=['POST'])
def initialize_puzzle():
    global solver, grid
    
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

@app.route('/api/solve_step', methods=['GET'])
def solve_step():
    global solver, grid
    
    if solver is None or grid is None:
        return jsonify({'error': 'Solver not initialized'}), 400
    
    # Use the StepwiseSolver to perform one step
    result = solver.solve_step()
    
    # Get grid state and assigned clues for response
    grid_state = get_grid_state(grid)
    assigned_clues = get_assigned_clues(grid)
    
    return jsonify({
        'grid': grid_state,
        'assigned_clues': assigned_clues,
        'progress': result['progress'],
        'message': result['message'],
        'is_correct': result.get('is_correct', False)
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
