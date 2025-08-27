
from datetime import datetime, timedelta

# Challenge templates with recurrence type
_challenge_templates = [
    {
        "title": "Global Cuisine - Weekly",
        "description": "Cook dishes from the most countries this week!",
        "participants_count": 12,
        "difficulty": "Intermediate",
        "recurrence": "weekly"
    },
    {
        "title": "Global Cuisine - Monthly",
        "description": "Cook and log dishes from the most countries this month!",
        "participants_count": 45,
        "difficulty": "Advanced",
        "recurrence": "monthly"
    },
    {
        "title": "Global Cuisine - Annually",
        "description": "Cook and log dishes from the most countries this year!",
        "participants_count": 45,
        "difficulty": "Advanced",
        "recurrence": "annual"
    },
    {
        "title": "Recipe Master",
        "description": "Upload the most recipes this week and earn the Recipe Master title.",
        "participants_count": 30,
        "difficulty": "Beginner",
        "recurrence": "weekly"
    },
    {
        "title": "Recipe Sharer",
        "description": "Share the most publicly viewable recipes in a week!",
        "participants_count": 18,
        "difficulty": "All Levels",
        "recurrence": "weekly"
    },
    {
        "title": "Ultimate Chef",
        "description": "Cook the most unique dishes this year!",
        "participants_count": 5,
        "difficulty": "Expert",
        "recurrence": "annual"
    },
]

def _get_period_end(recurrence: str, now=None):
    """
    Returns the end datetime for the current recurrence period.
    """
    if now is None:
        now = datetime.utcnow()
    if recurrence == "weekly":
        # End of current week (Sunday 23:59:59 UTC)
        days_ahead = 6 - now.weekday()  # Monday=0, Sunday=6
        end = now + timedelta(days=days_ahead)
        return end.replace(hour=23, minute=59, second=59, microsecond=0)
    elif recurrence == "monthly":
        # End of current month
        if now.month == 12:
            next_month = now.replace(year=now.year+1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month+1, day=1)
        end = next_month - timedelta(seconds=1)
        return end.replace(hour=23, minute=59, second=59, microsecond=0)
    elif recurrence == "annual":
        # End of current year
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0)
        return end
    else:
        # Default: 7 days from now
        return now + timedelta(days=7)

def get_current_challenges():
    """
    Returns a list of current challenges with dynamically calculated end dates.
    """
    now = datetime.utcnow()
    challenges = []
    for template in _challenge_templates:
        challenge = template.copy()
        challenge["end_date"] = _get_period_end(template["recurrence"], now)
        challenges.append(challenge)
    return challenges

# For backward compatibility, keep 'challenges' as a property
challenges = get_current_challenges()
