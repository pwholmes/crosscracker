from flask import Flask, render_template, jsonify
from typing import List, Dict, Any
from .entities import Grid
from .crossword_solver import CrosswordSolver
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
    
    # Create grid and solver with test clues
    #grid = Grid(EMPTY_TEST_GRID, TEST_CLUES, TEST_ANSWERS)
    grid = Grid(EMPTY_TEST_GRID, TEST_CLUES)
    solver = CrosswordSolver(grid)
    # Ensure all clues are reset to unassigned
    for clue in grid.clues:
        clue.assigned = None
    
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
    return jsonify({
        'grid': result.get('grid'),
        'assigned_clues': result.get('assigned_clues', []),
        'progress': result.get('progress', False),
        'solved': result.get('solved', False),
        'message': result.get('message', None)
    })

@app.route('/api/solve_all', methods=['GET'])
def solve_all():
    global solver, grid
    
    if solver is None or grid is None:
        return jsonify({'error': 'Solver not initialized'}), 400
    
    # Solve the puzzle
    result = solver.solve()
    
    return jsonify({
        'grid': result.get('grid'),
        'assigned_clues': result.get('assigned_clues', []),
        'progress': result.get('progress', False),
        'solved': result.get('solved', False),
        'message': result.get('message', None)
    })

if __name__ == '__main__':
    app.run(debug=True)
