from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from recipe_app.models.models import Recipe, User, RecipeReview, RecipePhoto, RecipeCollection, Follow, RecipeComment
from recipe_app.models.advanced_models import Challenge, ChallengeParticipation, RecipeVote
from recipe_app.db import db
from datetime import datetime
from recipe_app.main.analytics import UserEvent
import os
from werkzeug.utils import secure_filename

community_bp = Blueprint('community', __name__)


@community_bp.route('/')
@community_bp.route('/home')
def community_home():
    """Community home page"""
    if not current_user.is_authenticated:
        flash('Please log in to access community features', 'info')
        return redirect(url_for('main.login'))
    
    # Get featured recipes (only public ones)
    featured_recipes = Recipe.query.filter_by(
        is_featured=True,
        is_approved=True,
        is_private=False  # Only public recipes
    ).limit(6).all()
    
    # Get recent public approved recipes instead of complex trending query
    trending_recipes = Recipe.query.filter_by(
        is_approved=True,
        is_private=False  # Only public recipes
    ).order_by(Recipe.created_at.desc()).limit(6).all()
    
    # Add vote counts and favourites count to recipes
    for recipe in featured_recipes + trending_recipes:
        recipe.vote_counts = get_recipe_vote_counts(recipe.id)
        recipe.favourites_count = get_recipe_favourites_count(recipe.id)
    
    # Get user's recent activity
    recent_reviews = []
    if current_user.is_authenticated:
        recent_reviews = RecipeReview.query.filter_by(
            user_id=current_user.id
        ).order_by(RecipeReview.created_at.desc()).limit(5).all()
    
    # Get follow counts
    following_count = 0
    followers_count = 0
    if current_user.is_authenticated:
        following_count = Follow.query.filter_by(follower_id=current_user.id).count()
        followers_count = Follow.query.filter_by(followed_id=current_user.id).count()
    
    return render_template('community/home.html',
                         featured_recipes=featured_recipes,
                         trending_recipes=trending_recipes,
                         recent_reviews=recent_reviews,
                         following_count=following_count,
                         followers_count=followers_count)

@community_bp.route('/featured')
def featured_recipes():
    """Featured recipes page"""
    if not current_user.is_authenticated:
        flash('Please log in to access community features', 'info')
        return redirect(url_for('main.login'))
    
    featured_recipes = Recipe.query.filter_by(
        is_featured=True,
        is_approved=True
    ).order_by(Recipe.featured_at.desc()).all()
    
    return render_template('community/featured_recipes.html',
                         recipes=featured_recipes)

@community_bp.route('/collections')
def recipe_collections():
    """Recipe collections page"""
    if not current_user.is_authenticated:
        flash('Please log in to access community features', 'info')
        return redirect(url_for('main.login'))
    
    # Get user's collections
    user_collections = RecipeCollection.query.filter_by(
        user_id=current_user.id
    ).order_by(RecipeCollection.created_at.desc()).all()
    
    # Get public collections from other users
    public_collections = RecipeCollection.query.filter(
        RecipeCollection.is_public == True,
        RecipeCollection.user_id != current_user.id
    ).order_by(RecipeCollection.created_at.desc()).limit(12).all()
    
    return render_template('community/collections.html',
                         user_collections=user_collections,
                         public_collections=public_collections)

@community_bp.route('/recipes')
def community_recipes():
    """Community recipes page - all public recipes with ratings and favourites"""
    if not current_user.is_authenticated:
        flash('Please log in to access community features', 'info')
        return redirect(url_for('main.login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Get filter parameters
    sort_by = request.args.get('sort', 'newest')  # newest, popular, favourites
    cuisine_filter = request.args.get('cuisine', '')
    difficulty_filter = request.args.get('difficulty', '')
    search_query = request.args.get('search', '')
    
    # Base query for public recipes only
    query = Recipe.query.filter(
        Recipe.is_private == False,  # Only public recipes
        Recipe.is_approved == True   # Only approved recipes
    )
    
    # Apply search filter
    if search_query:
        query = query.filter(Recipe.title.contains(search_query))
    
    # Apply cuisine filter
    if cuisine_filter:
        query = query.filter(Recipe.cuisine_type == cuisine_filter)
    
    # Apply difficulty filter
    if difficulty_filter:
        query = query.filter(Recipe.difficulty == difficulty_filter)
    
    # Apply sorting with proper subqueries for counting
    if sort_by == 'newest':
        query = query.order_by(Recipe.created_at.desc())
    elif sort_by == 'popular':
        # Sort by number of votes (love_it votes specifically for popularity)
        from sqlalchemy import func
        love_votes_subquery = db.session.query(
            RecipeVote.recipe_id,
            func.count(RecipeVote.id).label('love_count')
        ).filter(RecipeVote.vote_type == 'love_it').group_by(RecipeVote.recipe_id).subquery()
        
        query = query.outerjoin(love_votes_subquery, Recipe.id == love_votes_subquery.c.recipe_id)\
                    .order_by(love_votes_subquery.c.love_count.desc().nullslast(), Recipe.created_at.desc())
    elif sort_by == 'favourites':
        # Sort by number of favourites
        from sqlalchemy import func
        from recipe_app.models.models import user_favourites
        
        favourites_subquery = db.session.query(
            user_favourites.c.recipe_id,
            func.count(user_favourites.c.user_id).label('favourites_count')
        ).group_by(user_favourites.c.recipe_id).subquery()
        
        query = query.outerjoin(favourites_subquery, Recipe.id == favourites_subquery.c.recipe_id)\
                    .order_by(favourites_subquery.c.favourites_count.desc().nullslast(), Recipe.created_at.desc())
    
    # Paginate results
    recipes = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Add vote counts and favourites count to each recipe
    for recipe in recipes.items:
        recipe.vote_counts = get_recipe_vote_counts(recipe.id)
        recipe.favourites_count = get_recipe_favourites_count(recipe.id)
    
    # Get unique cuisines for filter dropdown (from public recipes only)
    cuisines = db.session.query(Recipe.cuisine_type).filter(
        Recipe.cuisine_type.isnot(None),
        Recipe.is_approved == True,
        Recipe.is_private == False  # Only public recipes
    ).distinct().all()
    cuisines = [c[0] for c in cuisines if c[0]]
    
    # Get unique difficulties for filter dropdown (from public recipes only)
    difficulties = db.session.query(Recipe.difficulty).filter(
        Recipe.difficulty.isnot(None),
        Recipe.is_approved == True,
        Recipe.is_private == False  # Only public recipes
    ).distinct().all()
    difficulties = [d[0] for d in difficulties if d[0]]
    
    return render_template('community/recipes.html',
                         recipes=recipes,
                         cuisines=cuisines,
                         difficulties=difficulties,
                         current_sort=sort_by,
                         current_cuisine=cuisine_filter,
                         current_difficulty=difficulty_filter,
                         current_search=search_query)

def get_recipe_favourites_count(recipe_id):
    """Helper function to get favourites count for a recipe"""
    from recipe_app.models.models import user_favourites
    from sqlalchemy import func
    
    count = db.session.query(func.count(user_favourites.c.user_id))\
                     .filter(user_favourites.c.recipe_id == recipe_id)\
                     .scalar()
    return count or 0

@community_bp.route('/challenges')
def active_challenges():
    """Active cooking challenges page"""
    if not current_user.is_authenticated:
        flash('Please log in to access community features', 'info')
        return redirect(url_for('main.login'))
    
    if not current_user.can_access_feature('cooking_challenges'):
        flash('Cooking challenges require Premium plan', 'warning')
        return redirect(url_for('main.dashboard'))
    
    # For now, show a placeholder since challenges aren't fully implemented
    challenges = []
    
    return render_template('community/challenges.html',
                         challenges=challenges)

@community_bp.route('/top-contributors')
def top_contributors():
    """Top contributors page"""
    if not current_user.is_authenticated:
        flash('Please log in to access community features', 'info')
        return redirect(url_for('main.login'))
    
    # Get users with most recipe contributions
    top_users = User.query.join(Recipe).group_by(User.id).order_by(
        db.func.count(Recipe.id).desc()
    ).limit(10).all()
    
    return render_template('community/top_contributors.html',
                         top_users=top_users)

@community_bp.route('/recipe/<int:recipe_id>/review', methods=['POST'])
@login_required
def add_review(recipe_id):
    """Add a review to a recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Check if user already reviewed this recipe
    existing_review = RecipeReview.query.filter_by(
        recipe_id=recipe_id,
        user_id=current_user.id
    ).first()
    
    if existing_review:
        return jsonify({'success': False, 'error': 'You have already reviewed this recipe'}), 400
    
    data = request.get_json()
    rating = data.get('rating', 0)
    comment = data.get('comment', '').strip()
    
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
    
    review = RecipeReview(
        recipe_id=recipe_id,
        user_id=current_user.id,
        rating=rating,
        comment=comment,
        created_at=datetime.utcnow()
    )
    
    db.session.add(review)
    db.session.commit()
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='recipe_reviewed',
        event_data=f'Recipe: {recipe.title}, Rating: {rating}'
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Review added successfully',
        'review': {
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
            'user': review.user.username,
            'created_at': review.created_at.strftime('%B %d, %Y')
        }
    })


@community_bp.route('/recipe/<int:recipe_id>/comments', methods=['GET'])
def get_comments(recipe_id):
    """Return comment thread for a recipe"""
    Recipe.query.get_or_404(recipe_id)
    comments = RecipeComment.query.filter_by(
        recipe_id=recipe_id, parent_id=None
    ).order_by(RecipeComment.created_at.asc()).all()

    def serialize(comment):
        return {
            'id': comment.id,
            'user': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'replies': [serialize(reply) for reply in comment.replies]
        }

    return jsonify({'comments': [serialize(c) for c in comments]})


@community_bp.route('/recipe/<int:recipe_id>/comments', methods=['POST'])
@login_required
def add_comment(recipe_id):
    """Add a comment or reply to a recipe"""
    Recipe.query.get_or_404(recipe_id)
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')

    if not content:
        return jsonify({'success': False, 'error': 'Content is required'}), 400

    parent = None
    if parent_id:
        parent = RecipeComment.query.filter_by(id=parent_id, recipe_id=recipe_id).first()
        if not parent:
            return jsonify({'success': False, 'error': 'Invalid parent comment'}), 400

    comment = RecipeComment(
        recipe_id=recipe_id,
        user_id=current_user.id,
        content=content,
        parent=parent,
        created_at=datetime.utcnow()
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'success': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'user': comment.user.username,
            'created_at': comment.created_at.isoformat(),
            'parent_id': comment.parent_id
        }
    })

@community_bp.route('/recipe/<int:recipe_id>/photo', methods=['POST'])
@login_required
def upload_recipe_photo(recipe_id):
    """Upload a photo of tried recipe"""
    if not current_user.can_access_feature('community_photos'):
        flash('Photo uploads require Home+ plan', 'warning')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if 'photo' not in request.files:
        flash('No photo selected', 'error')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))
    
    file = request.files['photo']
    if file.filename == '':
        flash('No photo selected', 'error')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        flash('Invalid file type. Please upload PNG, JPG, JPEG, or GIF files only.', 'error')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))
    
    # Save file
    filename = secure_filename(f"recipe_{recipe_id}_{current_user.id}_{datetime.utcnow().timestamp()}.{file.filename.rsplit('.', 1)[1].lower()}")
    
    # Create uploads directory if it doesn't exist
    upload_folder = os.path.join('recipe_app', 'static', 'uploads', 'recipe_photos')
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    # Save to database
    photo = RecipePhoto(
        recipe_id=recipe_id,
        user_id=current_user.id,
        filename=filename,
        caption=request.form.get('caption', '').strip(),
        created_at=datetime.utcnow()
    )
    
    db.session.add(photo)
    db.session.commit()
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='recipe_photo_uploaded',
        event_data=f'Recipe: {recipe.title}'
    )
    db.session.add(event)
    db.session.commit()
    
    flash('Photo uploaded successfully!', 'success')
    return redirect(url_for('main.recipe', recipe_id=recipe_id))

@community_bp.route('/recipe/<int:recipe_id>/share')
@login_required
def share_recipe(recipe_id):
    """Share recipe on social media"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Generate share data
    share_data = {
        'title': recipe.title,
        'description': recipe.description or f'Check out this delicious {recipe.title} recipe!',
        'url': url_for('main.recipe', recipe_id=recipe_id, _external=True),
        'image': url_for('static', filename='bakebook.png', _external=True)  # Default image
    }
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='recipe_shared',
        event_data=f'Recipe: {recipe.title}'
    )
    db.session.add(event)
    db.session.commit()
    
    return render_template('share_recipe.html', recipe=recipe, share_data=share_data)

@community_bp.route('/collections')
@login_required
def my_collections():
    """View user's recipe collections"""
    collections = RecipeCollection.query.filter_by(user_id=current_user.id).all()
    return render_template('recipe_collections.html', collections=collections)

@community_bp.route('/collections/create', methods=['POST'])
@login_required
def create_collection():
    """Create a new recipe collection"""
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    is_public = data.get('is_public', False)
    
    if not name:
        return jsonify({'success': False, 'error': 'Collection name is required'}), 400
    
    # Check if collection name already exists for this user
    existing = RecipeCollection.query.filter_by(
        user_id=current_user.id,
        name=name
    ).first()
    
    if existing:
        return jsonify({'success': False, 'error': 'Collection name already exists'}), 400
    
    collection = RecipeCollection(
        user_id=current_user.id,
        name=name,
        description=description,
        is_public=is_public,
        created_at=datetime.utcnow()
    )
    
    db.session.add(collection)
    db.session.commit()
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='collection_created',
        event_data=f'Collection: {name}'
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Collection created successfully',
        'collection': {
            'id': collection.id,
            'name': collection.name,
            'description': collection.description
        }
    })

@community_bp.route('/collections/<int:collection_id>/add-recipe/<int:recipe_id>', methods=['POST'])
@login_required
def add_recipe_to_collection(collection_id, recipe_id):
    """Add a recipe to a collection"""
    collection = RecipeCollection.query.filter_by(
        id=collection_id,
        user_id=current_user.id
    ).first_or_404()
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Check if recipe is already in collection
    if recipe in collection.recipes:
        return jsonify({'success': False, 'error': 'Recipe already in collection'}), 400
    
    collection.recipes.append(recipe)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Recipe added to collection'})

@community_bp.route('/community/featured')
def featured_recipes_legacy():
    """Legacy route - redirect to main featured route"""
    return redirect(url_for('community.featured_recipes'))

@community_bp.route('/api/recipes/trending')
def trending_recipes():
    """API endpoint for trending recipes"""
    # Get recipes with most recent activity (reviews, photos, favourites)
    trending = Recipe.query.join(RecipeReview).group_by(Recipe.id).order_by(
        db.func.count(RecipeReview.id).desc()
    ).limit(10).all()
    
    recipes_data = []
    for recipe in trending:
        recipes_data.append({
            'id': recipe.id,
            'title': recipe.title,
            'description': recipe.description,
            'user': recipe.user.username,
            'rating': recipe.average_rating(),
            'review_count': recipe.reviews.count()
        })
    
    return jsonify({'recipes': recipes_data})

@community_bp.route('/api/recipes/trending')
def api_trending_recipes():
    """Return recent public approved recipes as 'trending' for mobile/web."""
    try:
        from sqlalchemy import desc
        recipes = Recipe.query.filter_by(
            is_approved=True,
            is_private=False
        ).order_by(desc(Recipe.created_at)).limit(20).all()
        return jsonify({'recipes': [
            {
                'id': r.id,
                'title': r.title,
                'image_url': (url_for('static', filename=f'uploads/{r.image_file}', _external=True)
                              if getattr(r, 'image_file', None) else None),
                'created_at': r.created_at.isoformat() if getattr(r, 'created_at', None) else None,
            } for r in recipes
        ]})
    except Exception as e:
        return jsonify({'recipes': [], 'error': str(e)}), 500


# ===============================
# POSITIVE VOTING SYSTEM
# ===============================

@community_bp.route('/vote', methods=['POST'])
@login_required
def vote_recipe():
    """Cast a positive vote on a recipe"""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        recipe_id = data.get('recipe_id')
        vote_type = data.get('vote_type')
    else:
        recipe_id = request.form.get('recipe_id')
        vote_type = request.form.get('vote_type')
    
    # Validate inputs
    if not recipe_id or not vote_type:
        return jsonify({'error': 'Missing recipe ID or vote type'}), 400
    
    try:
        recipe_id = int(recipe_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid recipe ID'}), 400
    
    # Validate vote type
    valid_votes = ['love_it', 'want_to_try', 'not_favourite']
    if vote_type not in valid_votes:
        return jsonify({'error': 'Invalid vote type'}), 400
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Check for existing vote
    existing_vote = RecipeVote.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote_type = vote_type
        existing_vote.created_at = datetime.utcnow()
    else:
        # Create new vote
        new_vote = RecipeVote(
            user_id=current_user.id,
            recipe_id=recipe_id,
            vote_type=vote_type
        )
        db.session.add(new_vote)
    
    try:
        db.session.commit()
        
        # Get vote counts for the recipe
        vote_counts = get_recipe_vote_counts(recipe_id)
        
        return jsonify({
            'success': True,
            'vote_counts': vote_counts,
            'user_vote': vote_type
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to save vote'}), 500

@community_bp.route('/recipe/<int:recipe_id>/votes')
def get_recipe_votes(recipe_id):
    """Get vote counts for a recipe"""
    vote_counts = get_recipe_vote_counts(recipe_id)
    
    user_vote = None
    if current_user.is_authenticated:
        user_vote_obj = RecipeVote.query.filter_by(
            user_id=current_user.id,
            recipe_id=recipe_id
        ).first()
        if user_vote_obj:
            user_vote = user_vote_obj.vote_type
    
    return jsonify({
        'vote_counts': vote_counts,
        'user_vote': user_vote
    })

def get_recipe_vote_counts(recipe_id):
    """Helper function to get vote counts for a recipe"""
    votes = RecipeVote.query.filter_by(recipe_id=recipe_id).all()
    counts = {
        'love_it': 0,
        'want_to_try': 0,
        'not_favourite': 0,
        'total': len(votes)
    }
    
    for vote in votes:
        counts[vote.vote_type] += 1
    
    return counts


# ===============================
# CHALLENGE SYSTEM
# ===============================

@community_bp.route('/challenges')
def challenges():
    """View all challenges"""
    if not current_user.is_authenticated:
        flash('Please log in to view challenges', 'info')
        return redirect(url_for('main.login'))
    
    # Get ongoing challenges
    ongoing = Challenge.query.filter(
        Challenge.is_active == True,
        Challenge.start_date <= datetime.utcnow(),
        Challenge.end_date >= datetime.utcnow()
    ).order_by(Challenge.end_date.asc()).all()
    
    # Get upcoming challenges
    upcoming = Challenge.query.filter(
        Challenge.is_active == True,
        Challenge.start_date > datetime.utcnow()
    ).order_by(Challenge.start_date.asc()).limit(5).all()
    
    # Get completed challenges
    completed = Challenge.query.filter(
        Challenge.end_date < datetime.utcnow()
    ).order_by(Challenge.end_date.desc()).limit(5).all()
    
    return render_template('community/challenges.html',
                         ongoing_challenges=ongoing,
                         upcoming_challenges=upcoming,
                         completed_challenges=completed)

@community_bp.route('/challenge/<int:challenge_id>')
def challenge_detail(challenge_id):
    """View challenge details"""
    if not current_user.is_authenticated:
        flash('Please log in to view challenge details', 'info')
        return redirect(url_for('main.login'))
    
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # Get user's participation
    user_participation = challenge.get_user_participation(current_user)
    
    # Get top participants for completed challenges
    top_participants = []
    if challenge.end_date < datetime.utcnow():
        top_participants = ChallengeParticipation.query.filter_by(
            challenge_id=challenge_id,
            is_completed=True
        ).order_by(ChallengeParticipation.score.desc()).limit(10).all()
    
    return render_template('community/challenge_detail.html',
                         challenge=challenge,
                         user_participation=user_participation,
                         top_participants=top_participants)

@community_bp.route('/challenge/<int:challenge_id>/join', methods=['POST'])
@login_required
def join_challenge(challenge_id):
    """Join a challenge"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if not challenge.can_join(current_user):
        flash('Cannot join this challenge', 'error')
        return redirect(url_for('community.challenge_detail', challenge_id=challenge_id))
    
    participation = ChallengeParticipation(
        challenge_id=challenge_id,
        user_id=current_user.id
    )
    
    try:
        db.session.add(participation)
        db.session.commit()
        flash(f'Successfully joined challenge: {challenge.title}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to join challenge', 'error')
    
    return redirect(url_for('community.challenge_detail', challenge_id=challenge_id))

@community_bp.route('/challenge/<int:challenge_id>/submit', methods=['POST'])
@login_required
def submit_to_challenge(challenge_id):
    """Submit a recipe to a challenge"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # Check if user is participating
    participation = challenge.get_user_participation(current_user)
    if not participation:
        flash('You must join the challenge first', 'error')
        return redirect(url_for('community.challenge_detail', challenge_id=challenge_id))
    
    recipe_id = request.form.get('recipe_id')
    submission_notes = request.form.get('submission_notes', '')
    
    if not recipe_id:
        flash('Please select a recipe to submit', 'error')
        return redirect(url_for('community.challenge_detail', challenge_id=challenge_id))
    
    # Verify user owns the recipe
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    if not recipe:
        flash('You can only submit your own recipes', 'error')
        return redirect(url_for('community.challenge_detail', challenge_id=challenge_id))
    
    # Update participation
    participation.submitted_recipe_id = recipe_id
    participation.submission_notes = submission_notes
    participation.submission_date = datetime.utcnow()
    participation.is_completed = True
    participation.completed_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash('Recipe submitted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to submit recipe', 'error')
    
    return redirect(url_for('community.challenge_detail', challenge_id=challenge_id))


# ===============================
# USER FOLLOWING SYSTEM
# ===============================

@community_bp.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    """Follow another user"""
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    user_to_follow = User.query.get_or_404(user_id)
    
    # Check if already following
    existing_follow = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()
    
    if existing_follow:
        return jsonify({'error': 'Already following this user'}), 400
    
    # Create follow relationship
    follow = Follow(
        follower_id=current_user.id,
        followed_id=user_id
    )
    
    try:
        db.session.add(follow)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Now following {user_to_follow.username}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to follow user'}), 500

@community_bp.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    """Unfollow a user"""
    follow = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()
    
    if not follow:
        return jsonify({'error': 'Not following this user'}), 400
    
    try:
        db.session.delete(follow)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Unfollowed successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to unfollow user'}), 500

@community_bp.route('/following')
@login_required
def following():
    """View users you're following"""
    following_relationships = Follow.query.filter_by(
        follower_id=current_user.id
    ).order_by(Follow.created_at.desc()).all()
    
    following_users = [rel.followed for rel in following_relationships]
    
    return render_template('community/following.html',
                         following_users=following_users)

@community_bp.route('/followers')
@login_required
def followers():
    """View your followers"""
    follower_relationships = Follow.query.filter_by(
        followed_id=current_user.id
    ).order_by(Follow.created_at.desc()).all()
    
    follower_users = [rel.follower for rel in follower_relationships]
    
    return render_template('community/followers.html',
                         follower_users=follower_users)
