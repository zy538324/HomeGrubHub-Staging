// Nutrition charts and utilities

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
    const data = JSON.parse(canvas.dataset.chart);
    if (canvas.id === 'nutritionChart') {
      renderNutritionProgress(canvas, data);
    } else if (canvas.id === 'weightChart') {
      renderWeightChart(canvas, data);
    } else if (canvas.id === 'waterChart') {
      renderWaterChart(canvas, data);
    }
  });

  const macro = document.getElementById('macroChart');
  if (macro && macro.dataset.protein) {
    renderMacroChart(macro);
  }
});

function renderNutritionProgress(canvas, data) {
  new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: data.dates,
      datasets: [
        { label: 'Calories', data: data.calories, borderColor: 'rgba(255,99,132,1)', fill: false },
        { label: 'Protein', data: data.protein, borderColor: 'rgba(54,162,235,1)', fill: false },
        { label: 'Carbs', data: data.carbs, borderColor: 'rgba(255,206,86,1)', fill: false },
        { label: 'Fat', data: data.fat, borderColor: 'rgba(75,192,192,1)', fill: false }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: 'Date' } },
        y: { title: { display: true, text: 'Amount' } }
      }
    }
  });
}

function renderWeightChart(canvas, data) {
  new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: data.dates,
      datasets: [{ label: 'Weight (kg)', data: data.weights, borderColor: 'rgba(54,162,235,1)', fill: false }]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: 'Date' } },
        y: { title: { display: true, text: 'Weight (kg)' } }
      }
    }
  });
}

function renderWaterChart(canvas, data) {
  new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: data.dates,
      datasets: [{ label: 'Water Intake (ml)', data: data.amounts, borderColor: 'rgba(75,192,192,1)', fill: false }]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: 'Date' } },
        y: { title: { display: true, text: 'Amount (ml)' } }
      }
    }
  });
}

function renderMacroChart(canvas) {
  const data = {
    protein: parseFloat(canvas.dataset.protein),
    carbs: parseFloat(canvas.dataset.carbs),
    fat: parseFloat(canvas.dataset.fat)
  };
  new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Protein', 'Carbohydrates', 'Fat'],
      datasets: [{
        data: [data.protein, data.carbs, data.fat],
        backgroundColor: ['var(--success-color)', 'var(--warning-color)', '#17a2b8'],
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } }
    }
  });
}

// Utility functions
function addToMealPlan() {
  alert('Add to meal plan functionality coming soon!');
}

function shareNutrition() {
  const title = document.title;
  const url = window.location.href;
  if (navigator.share) {
    navigator.share({ title: title, text: title, url: url });
  } else {
    navigator.clipboard.writeText(url);
    alert('Link copied to clipboard!');
  }
}

function printNutrition() {
  window.print();
}

