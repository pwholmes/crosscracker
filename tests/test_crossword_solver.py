import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.entities import Grid
from src.crossword_solver import CrosswordSolver
from data.test_data import EMPTY_TEST_GRID, TEST_CLUES

# Create and print the sample grid for verification
test_grid = Grid(EMPTY_TEST_GRID, TEST_CLUES)
print("Empty grid:\n")
test_grid.print()

# Initialize solver with test grid
solver = CrosswordSolver(test_grid)
solver.solve()
print("\nSolved grid:\n")
solver.grid.print()
