# Fitness & Weight Tracking Feature

## Overview

The Fitness & Weight Tracking feature provides comprehensive tools for users to monitor their weight, calculate BMI, and set safe weight goals. This feature emphasizes **health and safety** by enforcing the medically recommended maximum weight change of 2 pounds (0.9kg) per week.

## Features

### 1. Fitness Dashboard (`/fitness/dashboard`)
- **Quick access cards** for all fitness tools
- **Recent weight logs** display (last 5 entries)
- **Recent workout history** (ready for future workout logging)
- **Health & safety tips** with educational content
- Clean, responsive design with interactive cards

### 2. BMI Calculator (`/fitness/bmi-calculator`)
- **Real-time BMI calculation** using weight (kg) and height (cm)
- **BMI category classification**: Underweight, Normal, Overweight, Obese
- **Educational BMI information** with health risk indicators
- **Unit conversion helpers** for pounds/feet to metric
- **Colour-coded results** for easy interpretation

### 3. Safe Weight Goal Planner (`/fitness/weight-goal-planner`)
- **Safety enforcement**: Maximum 2 lbs (0.9kg) per week change
- **Automatic goal validation** with recommendations for unsafe goals
- **Uses current weight** from recent logs automatically
- **Visual feedback** on goal safety with colour coding
- **Educational content** on safe weight management
- **Alternative goal suggestions** when user goals are too aggressive

### 4. Weight Logging (`/fitness/log-weight-page`)
- **Simple weight entry form** with date selection
- **Optional body fat percentage** tracking
- **Notes field** for personal observations
- **Built-in weight converter** (pounds ↔ kilograms)
- **AJAX form submission** with success confirmation
- **Weight tracking tips** for consistency

### 5. Weight History (`/fitness/weight-history`)
- **Interactive weight chart** using Chart.js
- **Comprehensive statistics**:
  - Current weight
  - Total entries
  - Total weight change
  - Days tracked
- **Detailed history table** with:
  - Date and weight in kg/lbs
  - Body fat percentage (if logged)
  - Weight change from previous entry
  - Notes with tooltips
  - Delete functionality
- **Visual progress tracking** with trend analysis

## Safety Features

### 1. Weight Change Validation
```python
def calculate_safe_weight_change(current_weight, target_weight, weeks):
    """Calculate safe weight change ensuring no more than 2lbs per week"""
    weight_diff = target_weight - current_weight
    max_safe_change = 0.907 * weeks  # 2 lbs = 0.907 kg per week
    
    if abs(weight_diff) > max_safe_change:
        # Returns alternative safe recommendation
        return False, message, recommended_target
    
    return True, "Target weight is within safe limits.", target_weight
```

### 2. Educational Content
- BMI limitations and medical consultation advice
- Safe weight loss/gain guidelines
- Health risk indicators
- Importance of gradual changes

### 3. User Experience Safety
- Clear warnings about rapid weight changes
- Alternative recommendations for unsafe goals
- Emphasis on medical consultation
- Consistent messaging about health priorities

## Technical Implementation

### Database Models
- **WeightLog**: Daily weight entries with optional body fat percentage
- **WorkoutLog**: Workout sessions (ready for expansion)
- **ExerciseLog**: Individual exercises within workouts

### Routes Structure
```
/fitness/
├── dashboard              # Main fitness hub
├── bmi-calculator        # BMI calculation tool
├── weight-goal-planner   # Safe goal planning
├── log-weight-page       # Weight entry form
├── weight-history        # Historical data and charts
└── API endpoints:
    ├── /log-weight       # POST: Save weight entry
    ├── /weight-logs      # GET: Retrieve weight logs  
    ├── /log-workout      # POST: Save workout
    ├── /workout-logs     # GET: Retrieve workouts
    └── /weight-logs/<id> # DELETE: Remove weight entry
```

### Frontend Features
- **Responsive design** with Bootstrap 5
- **Interactive charts** with Chart.js
- **Real-time converters** for metric/imperial units
- **AJAX form handling** for smooth user experience
- **Custom CSS styling** with fitness-specific themes
- **Accessibility features** with proper ARIA labels

## Navigation Integration

The fitness feature is integrated into the main navigation under the "Meal Planning" dropdown:

```html
<li><a class="dropdown-item" href="{{ url_for('fitness.fitness_dashboard') }}">
  <i class="fas fa-heartbeat me-2"></i>Fitness & Weight Tracker
</a></li>
```

## Files Created/Modified

### New Files:
- `recipe_app/routes/fitness_routes.py` - Main routing logic
- `recipe_app/models/fitness_models.py` - Database models
- `recipe_app/templates/fitness/` - Template directory
  - `dashboard.html` - Main fitness dashboard
  - `bmi_calculator.html` - BMI calculation interface
  - `weight_goal_planner.html` - Safe goal planning tool
  - `log_weight.html` - Weight entry form
  - `weight_history.html` - Historical data display
- `recipe_app/static/css/fitness.css` - Custom styling

### Modified Files:
- `recipe_app/routes/__init__.py` - Added fitness_bp import
- `recipe_app/db.py` - Registered fitness blueprint
- `recipe_app/templates/base.html` - Added navigation link

## Usage Examples

### 1. Setting a Weight Loss Goal
1. Navigate to Fitness Dashboard
2. Click "Plan Goals"
3. Enter current weight: 80kg
4. Enter target weight: 70kg
5. Enter timeframe: 12 weeks
6. System calculates: 10kg ÷ 12 weeks = 0.83kg/week ✓ Safe!

### 2. Attempting Unsafe Goal
1. Same setup as above
2. Enter target weight: 65kg  
3. Enter timeframe: 8 weeks
4. System calculates: 15kg ÷ 8 weeks = 1.88kg/week ⚠️ Too Fast!
5. System recommends: Target 72.7kg instead for safety

### 3. Tracking Progress
1. Log weight daily/weekly using "Log Weight"
2. View progress in "Weight History"
3. Monitor trends with interactive chart
4. Celebrate safe, steady progress!

## Future Enhancements

### Planned Features:
- **Workout logging** with exercise database
- **Progress photos** with before/after comparisons
- **Body measurements** tracking (waist, arms, etc.)
- **Integration with nutrition tracker** for holistic health
- **Goal setting reminders** and notifications
- **Export data** functionality (PDF reports, CSV)
- **Social features** for accountability partners

### Advanced Features:
- **Predictive analytics** for goal achievement
- **Integration with fitness wearables**
- **Personalised recommendations** based on progress
- **Medical professional dashboard** for healthcare providers

## Safety Disclaimer

This feature is designed as a **wellness tracking tool** and should not replace medical advice. Users are consistently reminded to:

- Consult healthcare professionals before significant weight changes
- Consider individual health conditions and medications  
- Focus on overall health rather than just weight numbers
- Seek professional guidance for eating disorders or medical conditions

The 2-pound-per-week limit is enforced as a **hard safety constraint** and cannot be overridden by users.

## Getting Started

1. **Access**: Navigate to Meal Planning → Fitness & Weight Tracker
2. **First Steps**: 
   - Calculate your BMI to understand current status
   - Log your current weight to establish baseline
   - Set realistic, safe goals using the planner
3. **Daily Use**: Log weight consistently (same time, same conditions)
4. **Monitor**: Review progress weekly in Weight History
5. **Adjust**: Modify goals as needed while maintaining safety limits

The fitness feature promotes sustainable, healthy approaches to weight management while providing the tools and data users need to succeed safely.
