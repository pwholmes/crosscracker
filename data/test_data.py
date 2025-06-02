from src.entities import Clue

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
    Clue(1, 'A', "One of a matched pair", 4, 0, 1),
    Clue(5, 'A', "Exclamation of surprise", 4, 1, 1),
    Clue(6, 'A', "Fruit used to make wine", 5, 2, 0),
    Clue(7, 'A', "Land surrounded by water", 4, 3, 0),
    Clue(8, 'A', "Christmas song subject", 4, 4, 0),
    Clue(1, 'D', "Human trunk sans limbs and head", 5, 0, 1),
    Clue(2, 'D', "Giant marine mammal", 5, 0, 2),
    Clue(3, 'D', "Drive or urge onward", 5, 0, 3),
    Clue(4, 'D', "Science Guy Bill", 3, 0, 4),
    Clue(6, 'D', "Spirit in a martini", 3, 2, 0)
]

# Example: TEST_ANSWERS for use with the new Grid argument
TEST_ANSWERS = {
    (1, 'A'): [("SOCK", 70), ("TWIN", 60)],
    (5, 'A'): [("OHMY", 70), ("DAMN", 60)],
    (6, 'A'): [("GRAPE", 90), ("APPLE", 50)],
    (7, 'A'): [("ISLE", 80), ("BANK", 50)],
    (8, 'A'): [("SNOW", 90), ("NOEL", 70)],
    (1, 'D'): [("TORSO", 80), ("BELLY", 50)],
    (2, 'D'): [("WHALE", 90), ("OTTER", 20)],
    (3, 'D'): [("IMPEL", 80), ("FORCE", 50)],
    (4, 'D'): [("NYE", 100)],
    (6, 'D'): [("GIN", 90), ("RUM", 50)]
}
