# HomeGrubHub Nutrition Platform: Endpoints & Features

## Free Tier
- Manual food entry: `/nutrition/add-food`, `/api/foods`
- Barcode scan: `/nutrition/barcode-scan`, `/barcode-lookup`
- Basic nutrient breakdown: calories, protein, carbs, fat
- Meal logging: `/nutrition/log-meal`, `/api/meals`
- Recipe search/save (up to 5): `/nutrition/recipe-search`, `/save-recipe`, `/delete-recipe`
- Shopping list: `/nutrition/shopping-list`, `/add-shopping-item`, `/delete-shopping-item`
- Weight logging: `/nutrition/log-weight`, `/weight-history`
- Step tracking: `/nutrition/log-steps`, `/step-history`
- Progress charts (7 days): `/nutrition/progress-chart`
- Meal plan template: `/nutrition/meal-plan`
- Water intake tracker: `/nutrition/log-water`, `/water-history`

## Home Tier (includes Free)
- Extended progress charts (30/90 days): `/nutrition/progress-chart-extended?days=30|90`
- Custom meal plan creation: `/nutrition/custom-meal-plan`
- Export nutrition logs (CSV): `/nutrition/export-nutrition-logs`
- Household sharing: `/nutrition/household`, `/add-household-member`, `/remove-household-member`

## Family Tier (includes Home)
- Shared family shopping list: `/nutrition/family-shopping-list`, `/family-add-shopping-item`, `/family-delete-shopping-item`
- Group meal logging: `/nutrition/group-log-meal`
- Shared progress chart: `/nutrition/family-progress-chart`
- Family meal plan template: `/nutrition/family-meal-plan`
- Family notifications/reminders: `/family-notification`

## Pro Tier (includes Family)
- Advanced analytics: `/nutrition/pro-analytics`
- AI/ML food recognition: `/nutrition/ai-food-recognition`
- Enhanced export (meals/foods): `/nutrition/pro-export`

## Student Tier (includes Pro)
- Campus group sharing: `/nutrition/campus-group`
- Study meal plan templates: `/nutrition/study-meal-plan`

---

## General
- All endpoints gated by user tier
- All features available via web UI and API
- Mobile integration points for barcode scan, wearable sync
- Household/campus features support multiple users

---

For details on request/response formats, see API documentation.
