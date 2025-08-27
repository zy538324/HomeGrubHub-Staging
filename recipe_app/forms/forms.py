from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, IntegerField, SelectField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, NumberRange, Regexp, Length
from recipe_app.models.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class RecipeForm(FlaskForm):
    title = StringField('Recipe Title', validators=[DataRequired()], 
                       render_kw={"placeholder": "Enter a descriptive title for your recipe"})
    description = TextAreaField('Description', validators=[Optional()],
                               render_kw={"placeholder": "Brief description of your recipe", "rows": 3})
    ingredients = TextAreaField('Ingredients', validators=[DataRequired()],
                               render_kw={"placeholder": "List ingredients (one per line or separated by commas)", "rows": 8})
    method = TextAreaField('Cooking Method', validators=[DataRequired()],
                          render_kw={"placeholder": "Step-by-step cooking instructions", "rows": 10})
    prep_time = IntegerField('Prep Time (minutes)', validators=[Optional(), NumberRange(min=0)],
                            render_kw={"placeholder": "Time to prepare ingredients"})
    cook_time = IntegerField('Cook Time (minutes)', validators=[Optional(), NumberRange(min=0)],
                            render_kw={"placeholder": "Time to cook the dish"})
    servings = IntegerField('Servings', validators=[Optional(), NumberRange(min=1)], default=4,
                           render_kw={"placeholder": "Number of people this serves"})
    difficulty = SelectField('Difficulty Level', 
                             choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')],
                             default='Medium')
    country = StringField('Country of Origin', validators=[Optional()],
                         render_kw={"placeholder": "e.g., Italy, France, India"})
    cuisine_type = StringField('Cuisine Type', validators=[Optional()],
                              render_kw={"placeholder": "e.g., Italian, Asian, Mediterranean"})
    tags = StringField('Tags (comma-separated)', validators=[Optional()],
                      render_kw={"placeholder": "e.g., vegetarian, quick, dessert, spicy"})
    
    # Nutrition Information (per serving)
    calories = FloatField('Calories per serving', validators=[Optional(), NumberRange(min=0, max=5000)],
                         render_kw={"placeholder": "e.g., 350", "step": "0.1"})
    protein_g = FloatField('Protein (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                          render_kw={"placeholder": "e.g., 25.5", "step": "0.1"})
    carbs_g = FloatField('Carbohydrates (g)', validators=[Optional(), NumberRange(min=0, max=500)],
                        render_kw={"placeholder": "e.g., 45.2", "step": "0.1"})
    fat_g = FloatField('Fat (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                      render_kw={"placeholder": "e.g., 12.3", "step": "0.1"})
    fiber_g = FloatField('Fiber (g)', validators=[Optional(), NumberRange(min=0, max=50)],
                        render_kw={"placeholder": "e.g., 8.1", "step": "0.1"})
    sugar_g = FloatField('Sugar (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                        render_kw={"placeholder": "e.g., 15.7", "step": "0.1"})
    sodium_mg = FloatField('Sodium (mg)', validators=[Optional(), NumberRange(min=0, max=5000)],
                          render_kw={"placeholder": "e.g., 320", "step": "0.1"})
    
    is_public = BooleanField('Make this recipe public', default=False)
    submit = SubmitField('Save Recipe')

class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()],
                   render_kw={"placeholder": "Search recipes, ingredients, or cuisines..."})
    submit = SubmitField('Search')

class RatingForm(FlaskForm):
    rating = SelectField('Rating', 
                        choices=[(5, '5 stars'), (4, '4 stars'), (3, '3 stars'), (2, '2 stars'), (1, '1 star')],
                        coerce=int, validators=[DataRequired()])
    comment = TextAreaField('Comment (optional)', validators=[Optional()],
                           render_kw={"placeholder": "Share your thoughts about this recipe", "rows": 4})
    submit = SubmitField('Submit Rating')

class ImportRecipeForm(FlaskForm):
    import_type = SelectField('Import Type', 
                             choices=[('url', 'Recipe URL'), ('rss', 'RSS Feed')],
                             default='url',
                             validators=[DataRequired()])
    url = StringField('URL', validators=[DataRequired()],
                     render_kw={"placeholder": "https://example.com/recipe or RSS feed URL"})
    max_items = IntegerField('Max Items', 
                           validators=[Optional(), NumberRange(min=1, max=50)],
                           default=10,
                           render_kw={"placeholder": "10"})
    submit = SubmitField('Import Recipe')

class EditImportedRecipeForm(FlaskForm):
    title = StringField('Recipe Title', validators=[DataRequired()], 
                       render_kw={"placeholder": "Enter a descriptive title for your recipe"})
    description = TextAreaField('Description', validators=[Optional()],
                               render_kw={"placeholder": "Brief description of your recipe", "rows": 3})
    ingredients = TextAreaField('Ingredients', validators=[DataRequired()],
                               render_kw={"placeholder": "List ingredients (one per line or separated by commas)", "rows": 8})
    method = TextAreaField('Cooking Method', validators=[DataRequired()],
                          render_kw={"placeholder": "Step-by-step cooking instructions", "rows": 10})
    prep_time = IntegerField('Prep Time (minutes)', validators=[Optional(), NumberRange(min=0)],
                            render_kw={"placeholder": "Time to prepare ingredients"})
    cook_time = IntegerField('Cook Time (minutes)', validators=[Optional(), NumberRange(min=0)],
                            render_kw={"placeholder": "Time to cook the dish"})
    servings = IntegerField('Servings', validators=[Optional(), NumberRange(min=1)], default=4,
                           render_kw={"placeholder": "Number of people this serves"})
    difficulty = SelectField('Difficulty Level', 
                             choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')],
                             default='Medium')
    country = StringField('Country of Origin', validators=[Optional()],
                         render_kw={"placeholder": "e.g., Italy, France, India"})
    cuisine_type = StringField('Cuisine Type', validators=[Optional()],
                              render_kw={"placeholder": "e.g., Italian, Asian, Mediterranean"})
    tags = StringField('Tags (comma-separated)', validators=[Optional()],
                      render_kw={"placeholder": "e.g., vegetarian, quick, dessert, spicy"})
    
    # Nutrition Information (per serving)
    calories = FloatField('Calories per serving', validators=[Optional(), NumberRange(min=0, max=5000)],
                         render_kw={"placeholder": "e.g., 350", "step": "0.1"})
    protein_g = FloatField('Protein (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                          render_kw={"placeholder": "e.g., 25.5", "step": "0.1"})
    carbs_g = FloatField('Carbohydrates (g)', validators=[Optional(), NumberRange(min=0, max=500)],
                        render_kw={"placeholder": "e.g., 45.2", "step": "0.1"})
    fat_g = FloatField('Fat (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                      render_kw={"placeholder": "e.g., 12.3", "step": "0.1"})
    fiber_g = FloatField('Fiber (g)', validators=[Optional(), NumberRange(min=0, max=50)],
                        render_kw={"placeholder": "e.g., 8.1", "step": "0.1"})
    sugar_g = FloatField('Sugar (g)', validators=[Optional(), NumberRange(min=0, max=200)],
                        render_kw={"placeholder": "e.g., 15.7", "step": "0.1"})
    sodium_mg = FloatField('Sodium (mg)', validators=[Optional(), NumberRange(min=0, max=5000)],
                          render_kw={"placeholder": "e.g., 320", "step": "0.1"})
    
    source_url = StringField('Source URL', validators=[Optional()],
                            render_kw={"readonly": True})
    is_public = BooleanField('Make this recipe public', default=False)
    save_recipe = SubmitField('Save Recipe')
    import_another = SubmitField('Import Another Recipe', render_kw={"formnovalidate": True})


class UserProfileForm(FlaskForm):
    """Form for updating user profile information"""
    username = StringField('Username', validators=[DataRequired()],
                          render_kw={"readonly": True})  # Username is typically not editable
    email = StringField('Email', validators=[DataRequired(), Email()],
                       render_kw={"placeholder": "your.email@example.com"})
    
    # Profile image upload
    profile_image = FileField('Profile Picture', 
                             validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                                                   'Images only! (jpg, jpeg, png, gif)')],
                             render_kw={"accept": "image/*"})
    
    # Enhanced profile fields
    display_name = StringField('Display Name', 
                              validators=[Optional(), Length(max=100)],
                              render_kw={"placeholder": "How you want to appear to other users"})
    profile_bio = TextAreaField('Bio', 
                               validators=[Optional(), Length(max=500)],
                               render_kw={"placeholder": "Tell the community about yourself, your cooking style, and interests...", 
                                        "rows": 4, "maxlength": "500"})
    
    # Social media links
    instagram_url = StringField('Instagram', 
                               validators=[Optional()],
                               render_kw={"placeholder": "https://instagram.com/yourusername"})
    youtube_url = StringField('YouTube', 
                             validators=[Optional()],
                             render_kw={"placeholder": "https://youtube.com/c/yourchannel"})
    website_url = StringField('Website', 
                             validators=[Optional()],
                             render_kw={"placeholder": "https://yourwebsite.com"})
    
    postcode = StringField('UK Postcode', validators=[Optional(), 
                          Regexp(r'^[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}$', 
                                message='Please enter a valid UK postcode (e.g., SW1A 1AA)')],
                          render_kw={"placeholder": "e.g., SW1A 1AA", 
                                   "pattern": "[A-Z]{1,2}[0-9][A-Z0-9]?\\s?[0-9][A-Z]{2}",
                                   "title": "UK postcode format (e.g., SW1A 1AA)"})
    
    # Privacy settings
    show_profile_publicly = BooleanField('Make profile visible in community', default=True)
    
    submit = SubmitField('Update Profile')
    
    def __init__(self, original_email, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Please use a different email address.')
