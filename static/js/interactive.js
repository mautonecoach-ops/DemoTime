// Interactive demo functionality for Flask Demo Platform

let counterValue = 0;
let interactionCount = 0;
let gridCells = [];
let dragDropActive = false;

// Initialize interactive features
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('clickCounter')) {
        initializeInteractiveDemo();
    }
});

// Initialize all interactive demo features
function initializeInteractiveDemo() {
    // Get initial counter value from server
    const initialCounter = document.getElementById('clickCounter').textContent;
    counterValue = parseInt(initialCounter) || 0;
    
    // Initialize interactive grid
    initializeGrid();
    
    // Initialize drag and drop
    initializeDragDrop();
    
    // Initialize progress tracking
    updateProgressBars();
    
    // Set up periodic updates
    setInterval(updateInteractionStats, 2000);
}

// Initialize interactive grid
function initializeGrid() {
    const grid = document.getElementById('interactiveGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    gridCells = [];
    
    // Create 6x6 grid
    for (let i = 0; i < 36; i++) {
        const cell = document.createElement('div');
        cell.className = 'grid-cell';
        cell.textContent = i + 1;
        cell.dataset.index = i;
        
        // Add click event
        cell.addEventListener('click', function() {
            toggleGridCell(this);
        });
        
        // Add double-click event
        cell.addEventListener('dblclick', function() {
            deactivateGridCell(this);
        });
        
        grid.appendChild(cell);
        gridCells.push(cell);
    }
}

// Toggle grid cell state
function toggleGridCell(cell) {
    cell.classList.toggle('active');
    interactionCount++;
    updateProgressBars();
    
    if (cell.classList.contains('active')) {
        cell.innerHTML = '<i class="fas fa-check"></i>';
    } else {
        cell.textContent = parseInt(cell.dataset.index) + 1;
    }
}

// Deactivate grid cell
function deactivateGridCell(cell) {
    cell.classList.remove('active');
    cell.textContent = parseInt(cell.dataset.index) + 1;
    interactionCount++;
    updateProgressBars();
}

// Initialize drag and drop
function initializeDragDrop() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files/text
    dropZone.addEventListener('drop', handleDrop, false);
    
    // Make the zone draggable for demo
    dropZone.addEventListener('dragstart', function(e) {
        e.dataTransfer.setData('text/plain', 'Demo drag data');
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    document.getElementById('dropZone').classList.add('drag-over');
}

function unhighlight(e) {
    document.getElementById('dropZone').classList.remove('drag-over');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const data = dt.getData('text/plain') || 'Dropped content';
    
    const resultDiv = document.getElementById('dropResult');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div class="alert alert-success mt-2">
                <i class="fas fa-check-circle me-2"></i>
                Drop successful! Content: "${data}"
            </div>
        `;
        
        setTimeout(() => {
            resultDiv.innerHTML = '';
        }, 3000);
    }
    
    interactionCount++;
    updateProgressBars();
}

// Increment counter via API
async function incrementCounter() {
    try {
        const response = await fetch('/api/counter/increment');
        const data = await response.json();
        
        if (data.value !== undefined) {
            counterValue = data.value;
            document.getElementById('clickCounter').textContent = counterValue;
            interactionCount++;
            updateProgressBars();
            
            // Add visual feedback
            const counter = document.getElementById('clickCounter');
            counter.classList.add('text-success');
            setTimeout(() => {
                counter.classList.remove('text-success');
            }, 500);
            
            if (window.DemoApp) {
                window.DemoApp.trackApiCall();
            }
        }
    } catch (error) {
        console.error('Error incrementing counter:', error);
        if (window.DemoApp) {
            window.DemoApp.showNotification('Failed to increment counter', 'danger');
        }
    }
}

// Get counter value from API
async function getCounterValue() {
    try {
        const response = await fetch('/api/counter/get');
        const data = await response.json();
        
        if (data.value !== undefined) {
            counterValue = data.value;
            document.getElementById('clickCounter').textContent = counterValue;
            
            if (window.DemoApp) {
                window.DemoApp.trackApiCall();
                window.DemoApp.showNotification('Counter value refreshed', 'info');
            }
        }
    } catch (error) {
        console.error('Error getting counter value:', error);
        if (window.DemoApp) {
            window.DemoApp.showNotification('Failed to get counter value', 'danger');
        }
    }
}

// Update theme color
function updateThemeColor() {
    const color = document.getElementById('colorPicker').value;
    
    // Update CSS custom properties
    document.documentElement.style.setProperty('--demo-primary-color', color);
    
    // Update various elements
    const elements = document.querySelectorAll('.btn-primary, .bg-primary, .text-primary');
    elements.forEach(el => {
        if (el.classList.contains('btn-primary')) {
            el.style.backgroundColor = color;
            el.style.borderColor = color;
        } else if (el.classList.contains('bg-primary')) {
            el.style.backgroundColor = color;
        } else if (el.classList.contains('text-primary')) {
            el.style.color = color;
        }
    });
    
    interactionCount++;
    updateProgressBars();
}

// Update font size
function updateFontSize() {
    const fontSize = document.getElementById('fontSizeRange').value;
    document.getElementById('fontSizeValue').textContent = fontSize + 'px';
    
    const dynamicText = document.getElementById('dynamicText');
    if (dynamicText) {
        dynamicText.style.fontSize = fontSize + 'px';
    }
    
    interactionCount++;
    updateProgressBars();
}

// Update dynamic text
function updateDynamicText() {
    const input = document.getElementById('textInput').value;
    const dynamicText = document.getElementById('dynamicText');
    const dynamicSubtext = document.getElementById('dynamicSubtext');
    
    if (dynamicText) {
        dynamicText.textContent = input || 'Interactive Demo Platform';
    }
    
    if (dynamicSubtext) {
        if (input) {
            dynamicSubtext.textContent = `You typed: "${input}" (${input.length} characters)`;
        } else {
            dynamicSubtext.textContent = 'Type in the input field to see real-time updates';
        }
    }
    
    interactionCount++;
    updateProgressBars();
}

// Toggle text case
function toggleTextCase() {
    const input = document.getElementById('textInput');
    const currentValue = input.value;
    
    if (currentValue === currentValue.toLowerCase()) {
        input.value = currentValue.toUpperCase();
    } else {
        input.value = currentValue.toLowerCase();
    }
    
    updateDynamicText();
}

// Reverse text
function reverseText() {
    const input = document.getElementById('textInput');
    input.value = input.value.split('').reverse().join('');
    updateDynamicText();
}

// Update progress bars
function updateProgressBars() {
    // Interaction progress (based on activity)
    const interactionPercent = Math.min(100, (interactionCount / 20) * 100);
    const interactionProgress = document.getElementById('interactionProgress');
    const interactionPercentElement = document.getElementById('interactionPercent');
    
    if (interactionProgress && interactionPercentElement) {
        interactionProgress.style.width = interactionPercent + '%';
        interactionPercentElement.textContent = Math.round(interactionPercent) + '%';
    }
    
    // Response time progress (simulated)
    const responsePercent = Math.random() * 30 + 70; // 70-100%
    const responseProgress = document.getElementById('responseProgress');
    const responsePercentElement = document.getElementById('responsePercent');
    
    if (responseProgress && responsePercentElement) {
        responseProgress.style.width = responsePercent + '%';
        responsePercentElement.textContent = Math.round(responsePercent) + '%';
    }
    
    // Completion progress (based on various factors)
    const activeCells = gridCells.filter(cell => cell.classList.contains('active')).length;
    const textLength = document.getElementById('textInput')?.value.length || 0;
    const completionPercent = Math.min(100, ((activeCells + textLength + interactionCount) / 50) * 100);
    
    const completionProgress = document.getElementById('completionProgress');
    const completionPercentElement = document.getElementById('completionPercent');
    
    if (completionProgress && completionPercentElement) {
        completionProgress.style.width = completionPercent + '%';
        completionPercentElement.textContent = Math.round(completionPercent) + '%';
    }
}

// Update interaction statistics
function updateInteractionStats() {
    // Update connection status
    const connectionStatus = document.getElementById('connectionStatus');
    if (connectionStatus) {
        const isOnline = navigator.onLine;
        connectionStatus.textContent = isOnline ? 'Connected' : 'Offline';
        connectionStatus.className = `badge ${isOnline ? 'bg-success' : 'bg-danger'} ms-2`;
    }
    
    // Update activity level
    const activityProgress = document.getElementById('activityProgress');
    if (activityProgress) {
        const now = Date.now();
        const timeSinceInteraction = now - (window.lastActivity || now);
        const activityLevel = Math.max(0, 100 - (timeSinceInteraction / 1000 * 5));
        activityProgress.style.width = activityLevel + '%';
    }
}

// Reset all interactions
function resetAll() {
    // Reset counter (visual only, not API)
    const counterDisplay = document.getElementById('clickCounter');
    if (counterDisplay) {
        counterDisplay.textContent = '0';
    }
    
    // Reset grid
    gridCells.forEach(cell => {
        cell.classList.remove('active');
        cell.textContent = parseInt(cell.dataset.index) + 1;
    });
    
    // Reset text input
    const textInput = document.getElementById('textInput');
    if (textInput) {
        textInput.value = '';
        updateDynamicText();
    }
    
    // Reset color picker
    const colorPicker = document.getElementById('colorPicker');
    if (colorPicker) {
        colorPicker.value = '#0d6efd';
        updateThemeColor();
    }
    
    // Reset font size
    const fontSizeRange = document.getElementById('fontSizeRange');
    if (fontSizeRange) {
        fontSizeRange.value = '16';
        updateFontSize();
    }
    
    // Reset interaction count
    interactionCount = 0;
    updateProgressBars();
    
    if (window.DemoApp) {
        window.DemoApp.showNotification('All interactions reset!', 'info');
    }
}

// Keyboard event handlers for interactive demo
document.addEventListener('keydown', function(e) {
    if (e.target.id === 'textInput') {
        // Allow normal typing in text input
        return;
    }
    
    // Demo-specific keyboard shortcuts
    switch(e.key) {
        case ' ':
            e.preventDefault();
            incrementCounter();
            break;
        case 'r':
            if (!e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                resetAll();
            }
            break;
        case 'g':
            e.preventDefault();
            // Activate random grid cell
            const inactiveCells = gridCells.filter(cell => !cell.classList.contains('active'));
            if (inactiveCells.length > 0) {
                const randomCell = inactiveCells[Math.floor(Math.random() * inactiveCells.length)];
                toggleGridCell(randomCell);
            }
            break;
    }
});
