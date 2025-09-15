document.addEventListener('DOMContentLoaded', function() {
  const foodsSelect = document.getElementById('foods');
  if (!foodsSelect) return;

  const foodsData = JSON.parse(foodsSelect.dataset.foods || '[]');

  foodsSelect.addEventListener('change', function() {
    const selected = Array.from(foodsSelect.selectedOptions).map(opt => parseInt(opt.value));
    const totals = {calories: 0, protein: 0, carbs: 0, fat: 0};

    foodsData.forEach(food => {
      if (selected.includes(food.id)) {
        totals.calories += food.calories;
        totals.protein += food.protein;
        totals.carbs += food.carbs;
        totals.fat += food.fat;
      }
    });

    document.getElementById('totalCalories').textContent = totals.calories;
    document.getElementById('totalProtein').textContent = totals.protein;
    document.getElementById('totalCarbs').textContent = totals.carbs;
    document.getElementById('totalFat').textContent = totals.fat;
  });
});
