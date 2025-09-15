
from .pantry_models import (
    PantryCategory,
    PantryItem,
    PantryUsageLog,
    ShoppingListItem as PantryShoppingListItem,  # Avoid name conflict
    WeeklyShoppingList,
    WeeklyShoppingItem,
)
from .advanced_models import (
    
    NutritionProfile,
    DietaryRestriction,
    user_dietary_restrictions,
    recipe_dietary_compliance,
    Equipment,
    recipe_equipment,
    user_equipment,
    SeasonalTag,
    recipe_seasonal_tags,
    MealPlan,
    MealPlanEntry,
    Ingredient,
    LegacyPantryItem,
    Store,
    IngredientPrice,
    UserPreferences,
    IngredientSubstitution,
    Challenge,
    ChallengeParticipation,
    ShoppingList,
    ShoppingListItem as AdvancedShoppingListItem  # Avoid name conflict
)
from .nutrition_models import (
    NutritionEntry,
    DailyNutritionSummary,
    NutritionGoal,
)
from .fitness_models import (
    WeightLog,
    WorkoutLog,
    ExerciseLog,
)
from .water_models import (
    WaterLog,
)
from .models import (
    Follow,
    User,
    Recipe,
    Tag,
    RecipeRating,
    RecipeReview,
    RecipePhoto,
    RecipeComment,
    RecipeCollection,
    recipe_tags,
    user_favourites,
    recipe_collections,
)

# Export the default ShoppingListItem (pantry version for meal planning)
ShoppingListItem = PantryShoppingListItem
