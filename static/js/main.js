// Main JavaScript file for Flask Demo Platform

// Global variables
let apiCallCount = 0;
let lastActivity = Date.now();

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask Demo Platform initialized');
    
    // Initialize components
    initializeNavigation();
    initializeTooltips();
    trackActivity();
    
    // Set up periodic updates
    setInterval(updateActivity, 1000);
});

// Navigation enhancement
function initializeNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Activity tracking
function trackActivity() {
    // Track mouse movement
    document.addEventListener('mousemove', () => {
        lastActivity = Date.now();
    });
    
    // Track keyboard activity
    document.addEventListener('keypress', () => {
        lastActivity = Date.now();
    });
    
    // Track clicks
    document.addEventListener('click', () => {
        lastActivity = Date.now();
    });
}

// Update activity indicators
function updateActivity() {
    const now = Date.now();
    const timeSinceActivity = now - lastActivity;
    
    // Update activity status if elements exist
    const activityIndicator = document.getElementById('activityProgress');
    if (activityIndicator) {
        const activityLevel = Math.max(0, 100 - (timeSinceActivity / 1000 * 10));
        activityIndicator.style.width = activityLevel + '%';
    }
    
    // Update last update time
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = new Date().toLocaleTimeString();
    }
}

// API call tracking
function trackApiCall() {
    apiCallCount++;
    const apiCountElement = document.getElementById('apiCallCount');
    if (apiCountElement) {
        apiCountElement.textContent = apiCallCount;
    }
}

// Utility function to show loading state
function showLoading(element, text = 'Loading...') {
    if (element) {
        const originalContent = element.innerHTML;
        element.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
        element.disabled = true;
        
        return () => {
            element.innerHTML = originalContent;
            element.disabled = false;
        };
    }
}

// Utility function to show notifications
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// Form validation enhancement
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (input.checkValidity()) {
                    input.classList.remove('is-invalid');
                    input.classList.add('is-valid');
                } else {
                    input.classList.remove('is-valid');
                    input.classList.add('is-invalid');
                }
            });
        });
    });
}

// Smooth scrolling for anchor links
function initializeSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 'k':
                e.preventDefault();
                // Increment counter if on interactive demo page
                if (typeof incrementCounter === 'function') {
                    incrementCounter();
                    showKeyboardFeedback('Counter incremented');
                }
                break;
            case 'r':
                e.preventDefault();
                // Refresh data
                location.reload();
                break;
            case 't':
                e.preventDefault();
                // Toggle theme (placeholder)
                showKeyboardFeedback('Theme toggle (demo)');
                break;
        }
    } else if (e.key === 'Escape') {
        // Reset actions
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
        
        if (typeof resetAll === 'function') {
            resetAll();
            showKeyboardFeedback('All interactions reset');
        }
    }
});

// Show keyboard shortcut feedback
function showKeyboardFeedback(message) {
    const feedbackElement = document.getElementById('keyboardFeedback');
    if (feedbackElement) {
        feedbackElement.textContent = message;
        feedbackElement.className = 'mt-3 text-success small';
        
        setTimeout(() => {
            feedbackElement.textContent = 'Press any shortcut to see feedback';
            feedbackElement.className = 'mt-3 text-muted small';
        }, 2000);
    }
}

// Utility function to format numbers
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

// Utility function to format dates
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

// Error handling for fetch requests
async function safeFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        trackApiCall();
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        showNotification(`API Error: ${error.message}`, 'danger');
        throw error;
    }
}

// Initialize enhanced features
document.addEventListener('DOMContentLoaded', function() {
    enhanceFormValidation();
    initializeSmoothScrolling();
});

// Export functions for use in other modules
window.DemoApp = {
    showLoading,
    showNotification,
    trackApiCall,
    safeFetch,
    formatNumber,
    formatDate
};
