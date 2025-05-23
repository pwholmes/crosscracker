# CrossCracker - Crossword Puzzle Solver with Web Interface

This project adds a web-based front end to a crossword puzzle solver, allowing users to watch the puzzle as it is being solved in real-time.

## Features

- Interactive web interface to visualize the crossword grid
- Step-by-step solving to watch the puzzle being solved incrementally
- Complete solving option to see the final solution
- Display of clues with their answers as they are solved

## Project Structure

- `src/crossword_solver.py`: Core crossword solving logic
- `src/app.py`: Flask web application that serves the frontend and API endpoints
- `src/templates/index.html`: HTML template for the web interface
- `src/static/css/style.css`: CSS styles for the web interface
- `src/static/js/script.js`: JavaScript code for the frontend logic
- `run.py`: Script to run the Flask application

## Installation

1. Clone the repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

1. Run the Flask application:

```bash
python run.py
```

2. Open your web browser and navigate to:

```
http://127.0.0.1:5000
```

## Using the Application

1. Click the "Initialize Puzzle" button to set up the crossword grid and clues.
2. Use the "Solve Step" button to solve the puzzle one step at a time, watching as answers are filled in.
3. Alternatively, use the "Solve All" button to solve the entire puzzle at once.
4. The solution progress is displayed at the bottom of the page.

## How It Works

The application uses a constraint propagation and backtracking algorithm to solve the crossword puzzle. Key algorithmic features include:

- **Confidence-Based Selection**: Clues with candidates having higher confidence scores are prioritized during solving
- **Chronological Backtracking**: The solver maintains the exact order of assignments and backtracks in LIFO (Last In, First Out) order
- **Constraint Propagation**: Ensures that all assigned words are compatible with each other at intersections

The web interface communicates with the Flask backend through API endpoints:

- `/api/initialize`: Sets up the puzzle grid and clues
- `/api/solve_step`: Performs one step of the solving process
- `/api/solve_all`: Solves the entire puzzle

The frontend updates the grid and clues in real-time as the puzzle is being solved.
