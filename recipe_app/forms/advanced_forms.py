from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SelectMultipleField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
from wtforms.widgets import CheckboxInput, ListWidget

class MultiCheckboxField(SelectMultipleField):
    """Custom field for multiple checkboxes"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class AdvancedFilterForm(FlaskForm):
    """Advanced recipe filtering form"""
    
    # Basic search
    search_query = StringField('Search', validators=[Optional()],
                              render_kw={"placeholder": "Search recipes, ingredients, or cuisines..."})
    
    # Time filters
    max_prep_time = IntegerField('Max Prep Time (minutes)', validators=[Optional(), NumberRange(min=0, max=480)],
                                render_kw={"placeholder": "e.g., 30"})
    max_cook_time = IntegerField('Max Cook Time (minutes)', validators=[Optional(), NumberRange(min=0, max=480)],
                                render_kw={"placeholder": "e.g., 60"})
    max_total_time = IntegerField('Max Total Time (minutes)', validators=[Optional(), NumberRange(min=0, max=600)],
                                 render_kw={"placeholder": "e.g., 90"})
    
    # Difficulty and skill
    difficulty = MultiCheckboxField('Difficulty Level',
                                   choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')],
                                   validators=[Optional()])
    skill_level = MultiCheckboxField('Skill Level',
                                    choices=[('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'), 
                                           ('Advanced', 'Advanced'), ('Expert', 'Expert')],
                                    validators=[Optional()])
    
    # Servings
    min_servings = IntegerField('Min Servings', validators=[Optional(), NumberRange(min=1, max=20)],
                               render_kw={"placeholder": "1"})
    max_servings = IntegerField('Max Servings', validators=[Optional(), NumberRange(min=1, max=20)],
                               render_kw={"placeholder": "10"})
    
    # Nutrition filters
    max_calories = IntegerField('Max Calories per Serving', validators=[Optional(), NumberRange(min=0, max=2000)],
                               render_kw={"placeholder": "e.g., 500"})
    min_protein = FloatField('Min Protein (g)', validators=[Optional(), NumberRange(min=0, max=100)],
                            render_kw={"placeholder": "e.g., 20"})
    max_carbs = FloatField('Max Carbs (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                          render_kw={"placeholder": "e.g., 30"})
    max_fat = FloatField('Max Fat (g)', validators=[Optional(), NumberRange(min=0, max=100)],
                        render_kw={"placeholder": "e.g., 15"})
    min_fiber = FloatField('Min Fiber (g)', validators=[Optional(), NumberRange(min=0, max=50)],
                          render_kw={"placeholder": "e.g., 5"})
    max_sodium = FloatField('Max Sodium (mg)', validators=[Optional(), NumberRange(min=0, max=5000)],
                           render_kw={"placeholder": "e.g., 500"})
    
    # Nutritional flags
    nutritional_flags = MultiCheckboxField('Nutritional Benefits',
                                          choices=[
                                              ('is_high_protein', 'High Protein'),
                                              ('is_low_carb', 'Low Carb'),
                                              ('is_high_fiber', 'High Fiber'),
                                              ('is_low_sodium', 'Low Sodium'),
                                              ('is_iron_rich', 'Iron Rich')
                                          ],
                                          validators=[Optional()])
    
    # Dietary restrictions
    dietary_restrictions = MultiCheckboxField('Dietary Requirements',
                                             choices=[
                                                 ('vegetarian', 'Vegetarian'),
                                                 ('vegan', 'Vegan'),
                                                 ('gluten-free', 'Gluten-Free'),
                                                 ('dairy-free', 'Dairy-Free'),
                                                 ('nut-free', 'Nut-Free'),
                                                 ('low-fodmap', 'Low FODMAP'),
                                                 ('keto', 'Keto'),
                                                 ('paleo', 'Paleo'),
                                                 ('halal', 'Halal'),
                                                 ('kosher', 'Kosher')
                                             ],
                                             validators=[Optional()])
    
    # Equipment
    required_equipment = MultiCheckboxField('Available Equipment',
                                           choices=[
                                               ('oven', 'Oven'),
                                               ('stovetop', 'Stovetop'),
                                               ('microwave', 'Microwave'),
                                               ('slow_cooker', 'Slow Cooker'),
                                               ('pressure_cooker', 'Pressure Cooker'),
                                               ('air_fryer', 'Air Fryer'),
                                               ('grill', 'Grill'),
                                               ('food_processor', 'Food Processor'),
                                               ('blender', 'Blender'),
                                               ('stand_mixer', 'Stand Mixer'),
                                               ('no_cook', 'No Cooking Required')
                                           ],
                                           validators=[Optional()])
    
    # Cost filters
    max_cost_per_serving = FloatField('Max Cost per Serving (£)', validators=[Optional(), NumberRange(min=0, max=50)],
                                     render_kw={"placeholder": "e.g., 5.00"})
    
    # Seasonal and cuisine
    cuisine_type = MultiCheckboxField('Cuisine Type',
                                     choices=[
                                         ('italian', 'Italian'),
                                         ('chinese', 'Chinese'),
                                         ('indian', 'Indian'),
                                         ('mexican', 'Mexican'),
                                         ('thai', 'Thai'),
                                         ('french', 'French'),
                                         ('japanese', 'Japanese'),
                                         ('mediterranean', 'Mediterranean'),
                                         ('american', 'American'),
                                         ('british', 'British'),
                                         ('korean', 'Korean'),
                                         ('vietnamese', 'Vietnamese'),
                                         ('greek', 'Greek'),
                                         ('moroccan', 'Moroccan'),
                                         ('spanish', 'Spanish')
                                     ],
                                     validators=[Optional()])
    
    seasonal_preference = SelectField('Seasonal Preference',
                                     choices=[
                                         ('', 'Any Season'),
                                         ('spring', 'Spring'),
                                         ('summer', 'Summer'),
                                         ('autumn', 'Autumn'),
                                         ('winter', 'Winter'),
                                         ('current', 'Current Season')
                                     ],
                                     validators=[Optional()])
    
    # Meal type and occasion
    meal_type = MultiCheckboxField('Meal Type',
                                  choices=[
                                      ('breakfast', 'Breakfast'),
                                      ('lunch', 'Lunch'),
                                      ('dinner', 'Dinner'),
                                      ('snack', 'Snack'),
                                      ('dessert', 'Dessert'),
                                      ('appetizer', 'Appetizer'),
                                      ('side_dish', 'Side Dish'),
                                      ('beverage', 'Beverage')
                                  ],
                                  validators=[Optional()])
    
    # Recipe features
    has_image = BooleanField('Has Image')
    has_nutrition_info = BooleanField('Has Nutrition Information')
    has_batch_cooking = BooleanField('Suitable for Batch Cooking')
    freezer_friendly = BooleanField('Freezer Friendly')
    quick_prep = BooleanField('Quick Prep (≤ 15 min)')
    one_pot = BooleanField('One Pot/Pan')
    
    # Sorting options
    sort_by = SelectField('Sort By',
                         choices=[
                             ('relevance', 'Relevance'),
                             ('newest', 'Newest First'),
                             ('oldest', 'Oldest First'),
                             ('title_asc', 'Title A-Z'),
                             ('title_desc', 'Title Z-A'),
                             ('prep_time_asc', 'Prep Time (Shortest)'),
                             ('prep_time_desc', 'Prep Time (Longest)'),
                             ('total_time_asc', 'Total Time (Shortest)'),
                             ('total_time_desc', 'Total Time (Longest)'),
                             ('calories_asc', 'Calories (Lowest)'),
                             ('calories_desc', 'Calories (Highest)'),
                             ('cost_asc', 'Cost (Cheapest)'),
                             ('cost_desc', 'Cost (Most Expensive)'),
                             ('rating_desc', 'Highest Rated'),
                             ('difficulty_asc', 'Easiest First'),
                             ('difficulty_desc', 'Hardest First')
                         ],
                         default='relevance',
                         validators=[Optional()])
    
    # Pagination
    per_page = SelectField('Results per Page',
                          choices=[
                              ('12', '12 recipes'),
                              ('24', '24 recipes'),
                              ('48', '48 recipes'),
                              ('96', '96 recipes')
                          ],
                          default='24',
                          validators=[Optional()])
    
    # Form submission
    submit = SubmitField('Apply Filters')
    clear_filters = SubmitField('Clear All')


class NutritionAnalysisForm(FlaskForm):
    """Form for manual nutrition entry or API lookup"""
    
    # API options
    use_api = BooleanField('Auto-calculate nutrition', default=True)
    api_source = SelectField('Data Source',
                            choices=[
                                ('edamam', 'Edamam (Comprehensive)'),
                                ('spoonacular', 'Spoonacular (Recipe Focus)'),
                                ('usda', 'USDA (Database)')
                            ],
                            default='edamam')
    
    # Manual entry fields
    calories = FloatField('Calories per Serving', validators=[Optional(), NumberRange(min=0, max=5000)])
    protein_g = FloatField('Protein (g)', validators=[Optional(), NumberRange(min=0, max=200)])
    carbs_g = FloatField('Carbohydrates (g)', validators=[Optional(), NumberRange(min=0, max=500)])
    fat_g = FloatField('Fat (g)', validators=[Optional(), NumberRange(min=0, max=200)])
    fiber_g = FloatField('Fiber (g)', validators=[Optional(), NumberRange(min=0, max=100)])
    sugar_g = FloatField('Sugar (g)', validators=[Optional(), NumberRange(min=0, max=200)])
    sodium_mg = FloatField('Sodium (mg)', validators=[Optional(), NumberRange(min=0, max=10000)])
    
    # Additional micronutrients
    potassium_mg = FloatField('Potassium (mg)', validators=[Optional(), NumberRange(min=0, max=10000)])
    iron_mg = FloatField('Iron (mg)', validators=[Optional(), NumberRange(min=0, max=100)])
    calcium_mg = FloatField('Calcium (mg)', validators=[Optional(), NumberRange(min=0, max=5000)])
    vitamin_c_mg = FloatField('Vitamin C (mg)', validators=[Optional(), NumberRange(min=0, max=1000)])
    vitamin_d_ug = FloatField('Vitamin D (μg)', validators=[Optional(), NumberRange(min=0, max=100)])
    
    submit = SubmitField('Save Nutrition Data')


class MealPlannerForm(FlaskForm):
    """Form for creating and editing meal plans"""
    
    name = StringField('Meal Plan Name', validators=[DataRequired()],
                      render_kw={"placeholder": "e.g., 'Week of Jan 15th' or 'Low Carb January'"})
    description = StringField('Description', validators=[Optional()],
                             render_kw={"placeholder": "Optional description for this meal plan"})
    
    # Date range
    start_date = StringField('Start Date', validators=[DataRequired()],
                            render_kw={"type": "date"})
    end_date = StringField('End Date', validators=[DataRequired()],
                          render_kw={"type": "date"})
    
    # Settings
    is_template = BooleanField('Save as Template', 
                              render_kw={"title": "Templates can be reused for future weeks"})
    
    # Dietary preferences for this plan
    dietary_focus = SelectField('Dietary Focus',
                               choices=[
                                   ('', 'No specific focus'),
                                   ('weight_loss', 'Weight Loss'),
                                   ('muscle_gain', 'Muscle Gain'),
                                   ('maintenance', 'Maintenance'),
                                   ('budget_friendly', 'Budget Friendly'),
                                   ('quick_meals', 'Quick & Easy'),
                                   ('family_friendly', 'Family Friendly'),
                                   ('batch_cooking', 'Batch Cooking Focus')
                               ],
                               validators=[Optional()])
    
    # Target nutrition for the plan
    daily_calorie_target = IntegerField('Daily Calorie Target', validators=[Optional(), NumberRange(min=800, max=5000)],
                                       render_kw={"placeholder": "e.g., 2000"})
    
    submit = SubmitField('Create Meal Plan')


class PantryItemForm(FlaskForm):
    """Form for adding items to pantry"""
    
    ingredient_name = StringField('Ingredient', validators=[DataRequired()],
                                 render_kw={"placeholder": "e.g., Chicken Breast, Tomatoes, Rice"})
    quantity = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0.1, max=1000)],
                         render_kw={"placeholder": "e.g., 2.5"})
    unit = SelectField('Unit',
                      choices=[
                          ('pieces', 'pieces'),
                          ('kg', 'kg'),
                          ('g', 'grams'),
                          ('lbs', 'lbs'),
                          ('oz', 'oz'),
                          ('cups', 'cups'),
                          ('tbsp', 'tablespoons'),
                          ('tsp', 'teaspoons'),
                          ('ml', 'ml'),
                          ('l', 'litres'),
                          ('pints', 'pints'),
                          ('cans', 'cans'),
                          ('packets', 'packets'),
                          ('bottles', 'bottles')
                      ],
                      validators=[DataRequired()])
    
    # Optional fields
    purchase_date = StringField('Purchase Date', validators=[Optional()],
                               render_kw={"type": "date"})
    expiry_date = StringField('Expiry Date', validators=[Optional()],
                             render_kw={"type": "date"})
    cost = FloatField('Cost (£)', validators=[Optional(), NumberRange(min=0, max=1000)],
                     render_kw={"placeholder": "e.g., 3.50"})
    store = StringField('Store', validators=[Optional()],
                       render_kw={"placeholder": "e.g., Tesco, Sainsbury's"})
    notes = StringField('Notes', validators=[Optional()],
                       render_kw={"placeholder": "Any additional notes"})
    
    submit = SubmitField('Add to Pantry')


class QuickRecipeSuggestionsForm(FlaskForm):
    """Form for 'What can I cook?' feature"""
    
    available_ingredients = StringField('What do you have?', validators=[DataRequired()],
                                       render_kw={
                                           "placeholder": "List ingredients you have available (comma-separated)",
                                           "rows": 3
                                       })
    
    max_missing_ingredients = SelectField('Max missing ingredients',
                                         choices=[
                                             ('0', 'Use only what I have'),
                                             ('1', 'Up to 1 missing ingredient'),
                                             ('2', 'Up to 2 missing ingredients'),
                                             ('3', 'Up to 3 missing ingredients'),
                                             ('5', 'Up to 5 missing ingredients')
                                         ],
                                         default='2')
    
    meal_type = SelectField('Meal Type',
                           choices=[
                               ('', 'Any meal type'),
                               ('breakfast', 'Breakfast'),
                               ('lunch', 'Lunch'),
                               ('dinner', 'Dinner'),
                               ('snack', 'Snack'),
                               ('dessert', 'Dessert')
                           ],
                           validators=[Optional()])
    
    max_time = SelectField('Max cooking time',
                          choices=[
                              ('', 'Any time'),
                              ('15', '15 minutes'),
                              ('30', '30 minutes'),
                              ('45', '45 minutes'),
                              ('60', '1 hour'),
                              ('90', '1.5 hours'),
                              ('120', '2 hours')
                          ],
                          validators=[Optional()])
    
    difficulty = SelectField('Difficulty',
                            choices=[
                                ('', 'Any difficulty'),
                                ('Easy', 'Easy'),
                                ('Medium', 'Medium'),
                                ('Hard', 'Hard')
                            ],
                            validators=[Optional()])
    
    submit = SubmitField('Find Recipes')
