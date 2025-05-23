from src.crossword_solver import CrosswordSolver, Clue, Grid

# Sample 5x5 crossword grid for testing
# '#' denotes a black square.
EMPTY_TEST_GRID = [
    "#****",
    "#****",
    "*****",
    "****#",
    "****#",
]

# The same crossword grid, correctly solved
SOLVED_TEST_GRID = [
    "#TWIN",
    "#OHMY",
    "GRAPE",
    "ISLE#",
    "NOEL#",
]

# Clues for this sample grid
TEST_CLUES = [
    Clue(1, 'A', "One of a matched pair", 4, 0, 1, [("SOCK", 70), ("TWIN", 60)]),
    Clue(5, 'A', "Exclamation of surprise", 4, 1, 1, [("OHMY", 70), ("DAMN", 60)]),
    Clue(6, 'A', "Fruit used to make wine", 5, 2, 0, [("GRAPE", 90), ("APPLE", 50)]),
    Clue(7, 'A', "Land surrounded by water", 4, 3, 0, [("ISLE", 80), ("BANK", 50)]),
    Clue(8, 'A', "Christmas song subject", 4, 4, 0, [("SNOW", 90), ("NOEL", 70)]),
    Clue(1, 'D', "Human trunk sans limbs and head", 5, 0, 1, [("TORSO", 80), ("BELLY", 50)]),
    Clue(2, 'D', "Giant marine mammal", 5, 0, 2, [("WHALE", 90), ("OTTER", 20)]),
    Clue(3, 'D', "Drive or urge onward", 5, 0, 3, [("IMPEL", 80), ("FORCE", 50)]),
    Clue(4, 'D', "Science Guy Bill", 3, 0, 4, [("NYE", 100)]),
    Clue(6, 'D', "Spirit in a martini", 3, 2, 0, [("GIN", 90), ("RUM", 50)])
]

# Create and print the sample grid for verification
test_grid = Grid(EMPTY_TEST_GRID, TEST_CLUES)
print("Empty grid:\n")
test_grid.print()

# Initialize solver with test grid
solver = CrosswordSolver(test_grid)
solver.solve()
print("\nSolved grid:\n")
solver.grid.print()
