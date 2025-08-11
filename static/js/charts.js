// Charts functionality for Flask Demo Platform

let mainChart = null;
let trendChart = null;
let distributionChart = null;
let performanceChart = null;

// Chart configuration
const chartColors = {
    primary: '#0d6efd',
    success: '#198754',
    info: '#0dcaf0',
    warning: '#ffc107',
    danger: '#dc3545',
    secondary: '#6c757d'
};

// Initialize charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('mainChart')) {
        initializeMainChart();
        initializeMiniCharts();
        loadChartData();
    }
});

// Initialize main chart
function initializeMainChart() {
    const ctx = document.getElementById('mainChart').getContext('2d');
    
    mainChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Data Points',
                data: [],
                backgroundColor: chartColors.primary,
                borderColor: chartColors.primary,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Initialize mini charts
function initializeMiniCharts() {
    // Trend Chart
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        trendChart = new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Trend',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: chartColors.success,
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { display: false },
                    x: { display: false }
                }
            }
        });
    }

    // Distribution Chart
    const distributionCtx = document.getElementById('distributionChart');
    if (distributionCtx) {
        distributionChart = new Chart(distributionCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['General', 'Technical', 'Feedback'],
                datasets: [{
                    data: [30, 45, 25],
                    backgroundColor: [
                        chartColors.primary,
                        chartColors.success,
                        chartColors.info
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // Performance Chart
    const performanceCtx = document.getElementById('performanceChart');
    if (performanceCtx) {
        performanceChart = new Chart(performanceCtx.getContext('2d'), {
            type: 'polarArea',
            data: {
                labels: ['Speed', 'Efficiency', 'Accuracy', 'Reliability'],
                datasets: [{
                    data: [85, 92, 78, 95],
                    backgroundColor: [
                        chartColors.warning,
                        chartColors.success,
                        chartColors.info,
                        chartColors.primary
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    r: {
                        display: false
                    }
                }
            }
        });
    }
}

// Load chart data from API
async function loadChartData() {
    const dataSource = document.getElementById('dataSource')?.value || 'categories';
    
    try {
        let data;
        
        switch (dataSource) {
            case 'categories':
                data = await loadCategoryData();
                break;
            case 'monthly':
                data = await loadMonthlyData();
                break;
            case 'sample':
                data = generateSampleData();
                break;
            default:
                data = generateSampleData();
        }
        
        updateMainChart(data);
        updateChartInfo(data);
        
    } catch (error) {
        console.error('Error loading chart data:', error);
        // Fallback to sample data
        const fallbackData = generateSampleData();
        updateMainChart(fallbackData);
        updateChartInfo(fallbackData);
    }
}

// Load category data from API
async function loadCategoryData() {
    const response = await fetch('/api/stats');
    const stats = await response.json();
    
    const labels = Object.keys(stats.categories || {});
    const values = Object.values(stats.categories || {});
    
    return {
        labels: labels.length > 0 ? labels : ['No Data'],
        values: values.length > 0 ? values : [0],
        title: 'Form Submissions by Category'
    };
}

// Load monthly data (simulated)
async function loadMonthlyData() {
    // In a real app, this would come from an API
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const values = months.map(() => Math.floor(Math.random() * 50) + 10);
    
    return {
        labels: months,
        values: values,
        title: 'Monthly Submissions'
    };
}

// Generate sample data
function generateSampleData() {
    const categories = ['Web Development', 'Data Science', 'Mobile Apps', 'DevOps', 'Security'];
    const values = categories.map(() => Math.floor(Math.random() * 100) + 10);
    
    return {
        labels: categories,
        values: values,
        title: 'Sample Technology Areas'
    };
}

// Update main chart with new data
function updateMainChart(data) {
    if (!mainChart) return;
    
    mainChart.data.labels = data.labels;
    mainChart.data.datasets[0].data = data.values;
    mainChart.data.datasets[0].label = data.title;
    
    // Update colors based on chart type
    const chartType = document.getElementById('chartType')?.value || 'bar';
    updateChartColors(chartType);
    
    mainChart.update('active');
    
    // Update data point count
    const dataPointElement = document.getElementById('dataPointCount');
    if (dataPointElement) {
        dataPointElement.textContent = data.values.length;
    }
}

// Update chart colors based on type
function updateChartColors(chartType) {
    if (!mainChart) return;
    
    const dataset = mainChart.data.datasets[0];
    
    if (chartType === 'pie' || chartType === 'doughnut') {
        dataset.backgroundColor = [
            chartColors.primary,
            chartColors.success,
            chartColors.info,
            chartColors.warning,
            chartColors.danger,
            chartColors.secondary
        ];
    } else {
        dataset.backgroundColor = chartColors.primary;
        dataset.borderColor = chartColors.primary;
    }
}

// Update chart information
function updateChartInfo(data) {
    const total = data.values.reduce((sum, val) => sum + val, 0);
    const average = data.values.length > 0 ? Math.round(total / data.values.length) : 0;
    
    // Update totals
    const totalElement = document.getElementById('totalValue');
    if (totalElement) {
        totalElement.textContent = total;
    }
    
    const averageElement = document.getElementById('averageValue');
    if (averageElement) {
        averageElement.textContent = average;
    }
    
    // Find top category
    const maxValue = Math.max(...data.values);
    const maxIndex = data.values.indexOf(maxValue);
    
    const topCategoryElement = document.getElementById('topCategory');
    const topCategoryValueElement = document.getElementById('topCategoryValue');
    
    if (topCategoryElement && topCategoryValueElement && maxIndex >= 0) {
        topCategoryElement.textContent = data.labels[maxIndex];
        topCategoryValueElement.textContent = `${maxValue} entries`;
    }
    
    // Update last updated time
    const lastUpdatedElement = document.getElementById('lastUpdated');
    if (lastUpdatedElement) {
        lastUpdatedElement.textContent = new Date().toLocaleTimeString();
    }
}

// Change chart type
function changeChartType() {
    const chartType = document.getElementById('chartType').value;
    
    if (!mainChart) return;
    
    // Update current chart type display
    const currentTypeElement = document.getElementById('currentChartType');
    if (currentTypeElement) {
        currentTypeElement.textContent = chartType.charAt(0).toUpperCase() + chartType.slice(1) + ' Chart';
    }
    
    // Destroy current chart and create new one
    mainChart.destroy();
    
    const ctx = document.getElementById('mainChart').getContext('2d');
    const currentData = { ...mainChart.data };
    
    mainChart = new Chart(ctx, {
        type: chartType,
        data: currentData,
        options: getChartOptions(chartType)
    });
    
    updateChartColors(chartType);
    mainChart.update();
}

// Get chart options based on type
function getChartOptions(chartType) {
    const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: document.getElementById('showLegend')?.checked !== false,
                position: 'top'
            },
            tooltip: {
                enabled: document.getElementById('showTooltips')?.checked !== false
            }
        },
        animation: {
            duration: document.getElementById('showAnimation')?.checked !== false ? 1000 : 0
        }
    };
    
    if (chartType === 'pie' || chartType === 'doughnut') {
        return baseOptions;
    } else if (chartType === 'radar') {
        return {
            ...baseOptions,
            scales: {
                r: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        };
    } else {
        return {
            ...baseOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        };
    }
}

// Update chart options
function updateChartOptions() {
    if (!mainChart) return;
    
    const showLegend = document.getElementById('showLegend').checked;
    const showAnimation = document.getElementById('showAnimation').checked;
    const showTooltips = document.getElementById('showTooltips').checked;
    
    mainChart.options.plugins.legend.display = showLegend;
    mainChart.options.plugins.tooltip.enabled = showTooltips;
    mainChart.options.animation.duration = showAnimation ? 1000 : 0;
    
    mainChart.update();
}

// Refresh chart
function refreshChart() {
    loadChartData();
    
    // Show loading feedback
    const btn = event.target;
    const originalText = btn.innerHTML;
    const icon = btn.querySelector('i');
    
    icon.classList.add('fa-spin');
    
    setTimeout(() => {
        icon.classList.remove('fa-spin');
        if (window.DemoApp) {
            window.DemoApp.showNotification('Chart refreshed successfully!', 'success');
        }
    }, 1000);
}

// Randomize data
function randomizeData() {
    if (!mainChart) return;
    
    const newValues = mainChart.data.datasets[0].data.map(() => 
        Math.floor(Math.random() * 100) + 10
    );
    
    mainChart.data.datasets[0].data = newValues;
    mainChart.update('active');
    
    // Update chart info with new data
    updateChartInfo({
        labels: mainChart.data.labels,
        values: newValues,
        title: mainChart.data.datasets[0].label
    });
    
    if (window.DemoApp) {
        window.DemoApp.showNotification('Chart data randomized!', 'info');
    }
}

// Download chart (placeholder function)
function downloadChart() {
    if (!mainChart) return;
    
    const url = mainChart.toBase64Image();
    const link = document.createElement('a');
    link.download = 'chart.png';
    link.href = url;
    link.click();
    
    if (window.DemoApp) {
        window.DemoApp.showNotification('Chart downloaded!', 'success');
    }
}

// Fullscreen chart (placeholder function)
function fullscreenChart() {
    if (window.DemoApp) {
        window.DemoApp.showNotification('Fullscreen mode (demo)', 'info');
    }
}
