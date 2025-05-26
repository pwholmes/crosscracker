// DOM Elements
const initializeBtn = document.getElementById('initialize-btn');
const solveStepBtn = document.getElementById('solve-step-btn');
const solveAllBtn = document.getElementById('solve-all-btn');
const crosswordGrid = document.getElementById('crossword-grid');
const acrossCluesList = document.getElementById('across-clues-list');
const downCluesList = document.getElementById('down-clues-list');
const solutionStatus = document.getElementById('solution-status');

// Global variables
let gridData = null;
let acrossClues = [];
let downClues = [];
let cellNumbering = {};

// Event Listeners
initializeBtn.addEventListener('click', initializePuzzle);
solveStepBtn.addEventListener('click', solveStep);
solveAllBtn.addEventListener('click', solveAll);

// Functions
async function initializePuzzle() {
    try {
        solutionStatus.textContent = 'Initializing puzzle...';
        solutionStatus.className = '';
        
        const response = await fetch('/api/initialize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to initialize puzzle');
        }
        
        const data = await response.json();
        gridData = data.grid;
        acrossClues = data.across_clues;
        downClues = data.down_clues;
        
        // Create cell numbering map
        createCellNumbering();
        
        // Render the grid and clues
        renderGrid();
        renderClues();
        
        // Enable solve buttons
        solveStepBtn.disabled = false;
        solveAllBtn.disabled = false;
        
        solutionStatus.textContent = 'Puzzle initialized. Click "Solve Step" to start solving or "Solve All" to solve the entire puzzle.';
    } catch (error) {
        console.error('Error initializing puzzle:', error);
        solutionStatus.textContent = `Error: ${error.message}`;
    }
}

function createCellNumbering() {
    cellNumbering = {};
    
    // Process across clues
    acrossClues.forEach(clue => {
        const [row, col] = clue.start;
        const key = `${row}-${col}`;
        cellNumbering[key] = clue.number;
    });
    
    // Process down clues
    downClues.forEach(clue => {
        const [row, col] = clue.start;
        const key = `${row}-${col}`;
        if (!cellNumbering[key]) {
            cellNumbering[key] = clue.number;
        }
    });
}

function renderGrid() {
    // Clear the grid
    crosswordGrid.innerHTML = '';
    
    // Set grid columns based on the grid size
    if (gridData && gridData.length > 0) {
        crosswordGrid.style.gridTemplateColumns = `repeat(${gridData[0].length}, 1fr)`;
    }
    
    // Create cells
    gridData.forEach((row, rowIndex) => {
        row.forEach((cell, colIndex) => {
            const cellElement = document.createElement('div');
            cellElement.classList.add('cell');
            
            if (cell.is_black) {
                cellElement.classList.add('black');
            } else {
                // Add cell number if it exists
                const cellKey = `${rowIndex}-${colIndex}`;
                if (cellNumbering[cellKey]) {
                    const numberElement = document.createElement('span');
                    numberElement.classList.add('number');
                    numberElement.textContent = cellNumbering[cellKey];
                    cellElement.appendChild(numberElement);
                }
                
                // Add letter if it exists and is not a placeholder
                if (cell.char && cell.char !== '*') {
                    cellElement.textContent = cell.char;
                    cellElement.classList.add('filled');
                }
            }
            
            crosswordGrid.appendChild(cellElement);
        });
    });
}

function renderClues() {
    // Clear clue lists
    acrossCluesList.innerHTML = '';
    downCluesList.innerHTML = '';
    
    // Render across clues
    acrossClues.forEach(clue => {
        const listItem = document.createElement('li');
        listItem.id = `across-${clue.number}`;
        listItem.textContent = `${clue.number}. ${clue.text} (${clue.length})`;
        
        if (clue.assigned) {
            listItem.classList.add('solved');
            listItem.textContent += ` → ${clue.assigned}`;
        }
        
        acrossCluesList.appendChild(listItem);
    });
    
    // Render down clues
    downClues.forEach(clue => {
        const listItem = document.createElement('li');
        listItem.id = `down-${clue.number}`;
        listItem.textContent = `${clue.number}. ${clue.text} (${clue.length})`;
        
        if (clue.assigned) {
            listItem.classList.add('solved');
            listItem.textContent += ` → ${clue.assigned}`;
        }
        
        downCluesList.appendChild(listItem);
    });
}

async function solveStep() {
    try {
        solutionStatus.textContent = 'Solving step...';
        solutionStatus.className = '';
        
        const response = await fetch('/api/solve_step');
        
        if (!response.ok) {
            throw new Error('Failed to solve step');
        }
        
        const data = await response.json();
        console.log('Solve step response:', data);
        
        gridData = data.grid;
        
        // Update clues with assigned answers
        updateCluesWithAssignments(data.assigned_clues);
        
        // Re-render the grid and clues
        renderGrid();
        renderClues();
        
        // Update status with message from server
        if (data.message) {
            solutionStatus.textContent = data.message;
        } else if (data.progress) {
            solutionStatus.textContent = 'Step completed. Progress made!';
        } else {
            solutionStatus.textContent = 'Step completed. No further progress. Try "Solve All" to use backtracking.';
        }
        
        // If all clues are assigned, disable the solve step button
        const allSolved = acrossClues.every(clue => clue.assigned) && downClues.every(clue => clue.assigned);
        if (allSolved) {
            solveStepBtn.disabled = true;
            
            // Update status with correctness information
            if (data.solved === true) {
                solutionStatus.textContent = 'Puzzle solved correctly!';
                solutionStatus.classList.add('correct');
            } else if (data.solved === false) {
                solutionStatus.textContent = 'Puzzle solved, but the solution is incorrect.';
                solutionStatus.classList.add('incorrect');
            } else {
                solutionStatus.textContent = 'Puzzle solved! All clues have been assigned.';
            }
        }
    } catch (error) {
        console.error('Error solving step:', error);
        solutionStatus.textContent = `Error: ${error.message}`;
    }
}

function updateCluesWithAssignments(assignedClues) {
    if (!assignedClues) return;
    
    assignedClues.forEach(assigned => {
        if (assigned.direction === 'A') {
            const clue = acrossClues.find(c => c.number === assigned.number);
            if (clue) {
                clue.assigned = assigned.assigned;
            }
        } else {
            const clue = downClues.find(c => c.number === assigned.number);
            if (clue) {
                clue.assigned = assigned.assigned;
            }
        }
    });
}

async function solveAll() {
    try {
        solutionStatus.textContent = 'Solving puzzle step by step...';
        solutionStatus.className = '';
        solveStepBtn.disabled = true;
        solveAllBtn.disabled = true;
        
        let allSolved = false;
        
        while (!allSolved) {
            // Delay between steps
            await new Promise(resolve => setTimeout(resolve, 500));
            
            const response = await fetch('/api/solve_step');
            
            if (!response.ok) {
                throw new Error('Failed to solve step');
            }
            
            const data = await response.json();
            gridData = data.grid;
            
            // Update clues with assigned answers
            updateCluesWithAssignments(data.assigned_clues);
            
            // Re-render the grid and clues
            renderGrid();
            renderClues();
            
            // Update status
            if (data.message) {
                solutionStatus.textContent = data.message;
            }
            
            // Check if all clues are assigned
            allSolved = acrossClues.every(clue => clue.assigned) && 
                        downClues.every(clue => clue.assigned) ||
                        !data.progress;
                        
            // Update status with correctness information if puzzle is solved
            if (allSolved && data.solved !== undefined) {
                if (data.solved === true) {
                    solutionStatus.textContent = 'Puzzle solved correctly!';
                    solutionStatus.classList.add('correct');
                } else {
                    solutionStatus.textContent = 'Puzzle solved, but the solution is incorrect.';
                    solutionStatus.classList.add('incorrect');
                }
            }
        }
        
        solveAllBtn.disabled = true;
    } catch (error) {
        console.error('Error solving puzzle:', error);
        solutionStatus.textContent = `Error: ${error.message}`;
        solveStepBtn.disabled = false;
        solveAllBtn.disabled = false;
    }
}
