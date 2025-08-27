/**
 * Advanced Nutrition Tracker JavaScript
 * Handles interactive features, charts, and API calls for the nutrition tracking system
 */

class NutritionTracker {
    constructor() {
        this.currentDate = new Date();
        this.charts = {};
        this.waterGoal = 2000;
        this.initialize();
    }

    initialize() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadTodayData();
        this.setupProgressAnimations();
        this.fetchWaterSummary();
    }

    setupEventListeners() {
        // Add entry modal
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="add-entry"]')) {
                this.showAddEntryModal(e.target.dataset.mealType);
            }
        });

        // Date navigation
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="prev-date"]')) {
                this.changeDate(-1);
            } else if (e.target.matches('[data-action="next-date"]')) {
                this.changeDate(1);
            }
        });

        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.id === 'addEntryForm') {
                e.preventDefault();
                this.submitNutritionEntry();
            } else if (e.target.id === 'goalsForm') {
                e.preventDefault();
                this.saveGoals();
            }
        });

        // Real-time nutrition calculation
        document.addEventListener('input', (e) => {
            if (e.target.matches('#portion-size, #servings')) {
                this.calculateNutritionValues();
            }
        });

        // Auto-complete for product names
        this.setupProductAutocomplete();
    }

    initializeCharts() {
        this.initializeWeeklyChart();
        this.initializeMacroChart();
        this.initializeProgressCharts();
    }

    initializeWeeklyChart() {
        const canvas = document.getElementById('weeklyChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Get data from template variables
        const weekData = window.weeklyNutritionData || {
            labels: [],
            calories: [],
            protein: [],
            carbs: [],
            fat: []
        };

        this.charts.weekly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: weekData.labels,
                datasets: [{
                    label: 'Calories',
                    data: weekData.calories,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Protein (cal)',
                    data: weekData.protein.map(p => p * 4),
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: false
                }, {
                    label: 'Carbs (cal)',
                    data: weekData.carbs.map(c => c * 4),
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    tension: 0.4,
                    fill: false
                }, {
                    label: 'Fat (cal)',
                    data: weekData.fat.map(f => f * 9),
                    borderColor: '#9b59b6',
                    backgroundColor: 'rgba(155, 89, 182, 0.1)',
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#27ae60',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            title: function(tooltipItems) {
                                return 'Date: ' + tooltipItems[0].label;
                            },
                            afterBody: function(tooltipItems) {
                                const calories = tooltipItems[0].raw;
                                return `Total: ${Math.round(calories)} calories`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return Math.round(value) + ' cal';
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    initializeMacroChart() {
        const canvas = document.getElementById('macroChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Get today's macro data
        const macroData = window.todayMacroData || {
            protein: 0,
            carbs: 0,
            fat: 0
        };

        // Convert to calories
        const proteinCals = macroData.protein * 4;
        const carbsCals = macroData.carbs * 4;
        const fatCals = macroData.fat * 9;
        const total = proteinCals + carbsCals + fatCals;

        this.charts.macro = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Protein', 'Carbs', 'Fat'],
                datasets: [{
                    data: [proteinCals, carbsCals, fatCals],
                    backgroundColor: ['#3498db', '#f39c12', '#9b59b6'],
                    borderWidth: 0,
                    hoverBorderWidth: 3,
                    hoverBorderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                            generateLabels: function(chart) {
                                const data = chart.data;
                                if (data.labels.length && data.datasets.length) {
                                    return data.labels.map((label, i) => {
                                        const value = data.datasets[0].data[i];
                                        const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                        return {
                                            text: `${label}: ${Math.round(value)}cal (${percentage}%)`,
                                            fillStyle: data.datasets[0].backgroundColor[i],
                                            hidden: false,
                                            index: i
                                        };
                                    });
                                }
                                return [];
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${Math.round(value)} cal (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%',
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
    }

    initializeProgressCharts() {
        // Animate circular progress indicators
        document.querySelectorAll('.circular-progress').forEach((element, index) => {
            setTimeout(() => {
                this.animateCircularProgress(element);
            }, index * 200);
        });

        // Animate progress bars
        document.querySelectorAll('.macro-progress-bar').forEach((element, index) => {
            setTimeout(() => {
                const width = element.style.width;
                element.style.width = '0%';
                element.style.transition = 'width 1s ease-out';
                setTimeout(() => {
                    element.style.width = width;
                }, 100);
            }, index * 300);
        });
    }

    animateCircularProgress(element) {
        const circle = element.querySelector('.circular-progress-circle:last-child');
        if (!circle) return;

        const circumference = 2 * Math.PI * 32; // radius is 32
        const currentOffset = circle.style.strokeDashoffset || 0;
        
        circle.style.strokeDasharray = circumference;
        circle.style.strokeDashoffset = circumference;
        
        setTimeout(() => {
            circle.style.transition = 'stroke-dashoffset 1s ease-out';
            circle.style.strokeDashoffset = currentOffset;
        }, 100);
    }

    showAddEntryModal(mealType = 'breakfast') {
        const modal = document.getElementById('addEntryModal');
        if (!modal) return;

        // Set meal type
        const mealTypeSelect = document.getElementById('meal-type');
        if (mealTypeSelect) {
            mealTypeSelect.value = mealType;
        }

        // Reset form
        document.getElementById('addEntryForm').reset();
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    showGoalsModal() {
        const modal = document.getElementById('goalsModal');
        if (!modal) return;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    async submitNutritionEntry() {
        const form = document.getElementById('addEntryForm');
        const formData = new FormData(form);
        
        const entryData = {
            product_name: formData.get('product-name') || document.getElementById('product-name').value,
            brand: formData.get('brand') || document.getElementById('brand').value,
            portion_size: parseFloat(formData.get('portion-size') || document.getElementById('portion-size').value),
            servings: parseFloat(formData.get('servings') || document.getElementById('servings').value),
            meal_type: formData.get('meal-type') || document.getElementById('meal-type').value,
            notes: formData.get('notes') || document.getElementById('notes').value,
            nutrition: {
                calories: parseFloat(document.getElementById('calories').value) || 0,
                protein: parseFloat(document.getElementById('protein').value) || 0,
                carbs: parseFloat(document.getElementById('carbs').value) || 0,
                fat: parseFloat(document.getElementById('fat').value) || 0,
                fiber: parseFloat(document.getElementById('fiber').value) || 0,
                sugar: parseFloat(document.getElementById('sugar').value) || 0,
                sodium: parseFloat(document.getElementById('sodium').value) || 0
            }
        };

        try {
            this.showLoading('Adding entry...');
            
            const response = await fetch('/log-nutrition', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(entryData)
            });

            const result = await response.json();
            
            if (result.success) {
                this.hideLoading();
                this.showSuccess('Entry added successfully!');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addEntryModal'));
                modal.hide();
                
                // Refresh page or update UI
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.hideLoading();
                this.showError('Error adding entry: ' + result.error);
            }
        } catch (error) {
            this.hideLoading();
            this.showError('Error adding entry. Please try again.');
            console.error('Error:', error);
        }
    }

    async saveGoals() {
        const getValue = (id) => {
            const el = document.getElementById(id);
            return el ? parseFloat(el.value) : 0;
        };

        const goalsData = {
            daily_calories: getValue('goal-calories'),
            daily_protein: getValue('goal-protein'),
            daily_carbs: getValue('goal-carbs'),
            daily_fat: getValue('goal-fat'),
            daily_fiber: getValue('goal-fiber'),
            daily_sugar: getValue('goal-sugar'),
            daily_sodium: getValue('goal-sodium')
        };

        try {
            this.showLoading('Saving goals...');
            
            const response = await fetch('/nutrition/set-goals', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(goalsData)
            });

            const result = await response.json();
            
            if (result.success) {
                this.hideLoading();
                this.showSuccess('Goals saved successfully!');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('goalsModal'));
                modal.hide();
                
                // Update progress bars and refresh data
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.hideLoading();
                this.showError('Error saving goals: ' + result.error);
            }
        } catch (error) {
            this.hideLoading();
            this.showError('Error saving goals. Please try again.');
            console.error('Error:', error);
        }
    }

    changeDate(days) {
        this.currentDate.setDate(this.currentDate.getDate() + days);
        const formattedDate = this.currentDate.toISOString().split('T')[0];
        window.location.href = window.location.pathname + '?date=' + formattedDate;
    }

    calculateNutritionValues() {
        const portionSize = parseFloat(document.getElementById('portion-size').value) || 100;
        const servings = parseFloat(document.getElementById('servings').value) || 1;
        const multiplier = (portionSize / 100) * servings;

        // Update all nutrition fields based on per-100g values
        const fields = ['calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium'];
        
        fields.forEach(field => {
            const input = document.getElementById(field);
            if (input && input.dataset.per100g) {
                const per100g = parseFloat(input.dataset.per100g);
                input.value = (per100g * multiplier).toFixed(1);
            }
        });
    }

    setupProductAutocomplete() {
        const productNameInput = document.getElementById('product-name');
        if (!productNameInput) return;

        let debounceTimeout;
        
        productNameInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                this.searchProducts(e.target.value);
            }, 300);
        });
    }

    async searchProducts(query) {
        if (query.length < 3) return;

        try {
            const response = await fetch(`/api/products/search?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const products = await response.json();
            this.showProductSuggestions(products);
        } catch (error) {
            console.error('Error searching products:', error);
        }
    }

    showProductSuggestions(products) {
        // Create or update suggestions dropdown
        let dropdown = document.getElementById('product-suggestions');
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.id = 'product-suggestions';
            dropdown.className = 'product-suggestions';
            document.getElementById('product-name').parentNode.appendChild(dropdown);
        }

        dropdown.innerHTML = '';
        
        products.forEach(product => {
            const suggestion = document.createElement('div');
            suggestion.className = 'suggestion-item';
            suggestion.textContent = `${product.name} - ${product.brand}`;
            suggestion.addEventListener('click', () => {
                this.selectProduct(product);
                dropdown.style.display = 'none';
            });
            dropdown.appendChild(suggestion);
        });

        dropdown.style.display = products.length > 0 ? 'block' : 'none';
    }

    selectProduct(product) {
        document.getElementById('product-name').value = product.name;
        document.getElementById('brand').value = product.brand;
        
        // Fill nutrition data if available
        if (product.nutrition) {
            Object.keys(product.nutrition).forEach(key => {
                const input = document.getElementById(key);
                if (input) {
                    input.value = product.nutrition[key];
                    input.dataset.per100g = product.nutrition[key];
                }
            });
        }

        this.calculateNutritionValues();
    }

    setupProgressAnimations() {
        // Intersection observer for animation triggers
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate');
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.macro-card, .stat-item, .meal-section').forEach(el => {
            observer.observe(el);
        });
    }

    fetchWaterSummary() {
        const dateStr = this.currentDate.toISOString().split('T')[0];
        fetch(`/water-summary/${dateStr}`)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const total = data.total_ml || 0;
                    const percent = Math.min(100, (total / this.waterGoal) * 100);
                    const consumed = document.getElementById('water-consumed');
                    if (consumed) consumed.textContent = `${Math.round(total)}`;
                    const bar = document.getElementById('water-progress');
                    if (bar) bar.style.width = `${percent}%`;
                }
            })
            .catch(() => {});
    }

    logWater(amount) {
        this.showLoading('Logging water...');
        fetch('/log-water', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount_ml: amount })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    this.showSuccess('Water logged');
                    this.fetchWaterSummary();
                } else {
                    this.showError(data.error || 'Error logging water');
                }
            })
            .catch(() => this.showError('Error logging water'))
            .finally(() => this.hideLoading());
    }

    loadTodayData() {
        // This would typically load today's data via AJAX
        // For now, we'll use the data already rendered in the template
        console.log('Loading today\'s nutrition data...');
    }

    // Utility methods
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    showLoading(message = 'Loading...') {
        // Create or show loading indicator
        let loader = document.getElementById('nutrition-loader');
        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'nutrition-loader';
            loader.className = 'nutrition-loader';
            loader.innerHTML = `
                <div class="loader-content">
                    <div class="spinner"></div>
                    <p class="loader-message">${message}</p>
                </div>
            `;
            document.body.appendChild(loader);
        } else {
            loader.querySelector('.loader-message').textContent = message;
        }
        loader.style.display = 'flex';
    }

    hideLoading() {
        const loader = document.getElementById('nutrition-loader');
        if (loader) {
            loader.style.display = 'none';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `nutrition-toast nutrition-toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(toast);

        // Show toast
        setTimeout(() => toast.classList.add('show'), 100);

        // Hide and remove toast
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
}

// Utility functions
function showAddEntryModal(mealType) {
    if (window.nutritionTracker) {
        window.nutritionTracker.showAddEntryModal(mealType);
    }
}

function showGoalsModal() {
    if (window.nutritionTracker) {
        window.nutritionTracker.showGoalsModal();
    }
}

function showWaterLogPrompt() {
    if (window.nutritionTracker) {
        const amount = prompt('Water amount in ml', '250');
        if (amount) {
            const num = parseFloat(amount);
            if (!isNaN(num)) {
                window.nutritionTracker.logWater(num);
            }
        }
    }
}

function submitNutritionEntry() {
    if (window.nutritionTracker) {
        window.nutritionTracker.submitNutritionEntry();
    }
}

function saveGoals() {
    if (window.nutritionTracker) {
        window.nutritionTracker.saveGoals();
    }
}

function changeDate(days) {
    if (window.nutritionTracker) {
        window.nutritionTracker.changeDate(days);
    }
}

function editEntry(entryId) {
    // Implementation for editing existing entries
    console.log('Editing entry:', entryId);
    // This would open an edit modal or navigate to an edit page
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.nutritionTracker = new NutritionTracker();
    
    // Add custom CSS for dynamic elements
    const style = document.createElement('style');
    style.textContent = `
        .product-suggestions {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
            max-height: 200px;
            overflow-y: auto;
        }

        .suggestion-item {
            padding: 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        }

        .suggestion-item:hover {
            background: #f8f9fa;
        }

        .suggestion-item:last-child {
            border-bottom: none;
        }

        .nutrition-loader {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }

        .loader-content {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }

        .spinner {
            width: 40px;
            height: 40px;
            margin: 0 auto 1rem;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #27ae60;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loader-message {
            margin: 0;
            color: #333;
            font-weight: 600;
        }

        .nutrition-toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            z-index: 9999;
            transform: translateX(400px);
            opacity: 0;
            transition: all 0.3s ease;
        }

        .nutrition-toast.show {
            transform: translateX(0);
            opacity: 1;
        }

        .nutrition-toast-success {
            border-left: 4px solid #27ae60;
        }

        .nutrition-toast-error {
            border-left: 4px solid #e74c3c;
        }

        .toast-content {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .toast-content i {
            font-size: 1.2rem;
        }

        .nutrition-toast-success .toast-content i {
            color: #27ae60;
        }

        .nutrition-toast-error .toast-content i {
            color: #e74c3c;
        }

        .macro-card.animate,
        .stat-item.animate,
        .meal-section.animate {
            animation: slideInUp 0.6s ease-out forwards;
        }

        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
});
