# HomeGrubHub Nutrition Platform: API Requests & Responses

## Authentication
- All endpoints require user session (Flask `session['_user_id']`)
- Tier gating via `session['user_tier']`

## Example: Add Food
- Endpoint: `POST /api/foods`
- Request (JSON):
  ```json
  {
    "name": "Banana",
    "brand": "Dole",
    "barcode": "1234567890123",
    "calories": 89,
    "protein": 1.1,
    "carbs": 22.8,
    "fat": 0.3,
    "serving_size": "100g"
  }
  ```
- Response (JSON):
  ```json
  {
    "id": 1,
    "name": "Banana",
    "brand": "Dole",
    "barcode": "1234567890123",
    "calories": 89,
    "protein": 1.1,
    "carbs": 22.8,
    "fat": 0.3,
    "serving_size": "100g",
    "created_at": "2025-08-13T12:00:00"
  }
  ```

## Example: Log Meal
- Endpoint: `POST /api/meals`
- Request (JSON):
  ```json
  {
    "meal_type": "breakfast",
    "meal_date": "2025-08-13",
    "food_ids": [1, 2]
  }
  ```
- Response (JSON):
  ```json
  {
    "id": 1,
    "user_id": 1,
    "meal_type": "breakfast",
    "meal_date": "2025-08-13",
    "foods": [ ... ],
    "total_calories": 200,
    "total_protein": 10,
    "total_carbs": 30,
    "total_fat": 5,
    "created_at": "2025-08-13T12:05:00"
  }
  ```

## Example: Get Nutrition Logs
- Endpoint: `GET /api/nutrition-logs`
- Response (JSON):
  ```json
  [
    {
      "id": 1,
      "user_id": 1,
      "log_date": "2025-08-13",
      "meals": [ ... ],
      "daily_calories": 200,
      "daily_protein": 10,
      "daily_carbs": 30,
      "daily_fat": 5,
      "created_at": "2025-08-13T12:10:00"
    }
  ]
  ```

## Error Response (Tier Gating)
- Response (JSON):
  ```json
  { "error": "Feature not available for your tier." }
  ```

---

For more endpoints and details, see `ENDPOINTS_AND_FEATURES.md`.
