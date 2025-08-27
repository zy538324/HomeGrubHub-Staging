"""
Forms for pantry management
"""
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from datetime import date


class PantryItemForm(FlaskForm):
    """Form for editing pantry items"""
    name = StringField('Item Name', validators=[DataRequired(), Length(min=1, max=100)])
    brand = StringField('Brand', validators=[Optional(), Length(max=50)])
    
    current_quantity = FloatField('Current Quantity', validators=[DataRequired(), NumberRange(min=0)])
    unit = SelectField('Unit', choices=[
        ('units', 'Units'),
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('ml', 'Milliliters'),
        ('lbs', 'Pounds'),
        ('oz', 'Ounces'),
        ('cups', 'Cups'),
        ('tbsp', 'Tablespoons'),
        ('tsp', 'Teaspoons'),
        ('pieces', 'Pieces'),
        ('cans', 'Cans'),
        ('bottles', 'Bottles'),
        ('packages', 'Packages')
    ], validators=[DataRequired()])
    
    minimum_quantity = FloatField('Minimum Quantity (Alert Level)', 
                                validators=[DataRequired(), NumberRange(min=0)], default=1.0)
    ideal_quantity = FloatField('Ideal Quantity (Target Stock)', 
                              validators=[DataRequired(), NumberRange(min=0)], default=5.0)
    
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    storage_location = SelectField('Storage Location', choices=[
        ('', 'Not Specified'),
        ('Fridge', 'Refrigerator'),
        ('Freezer', 'Freezer'),
        ('Pantry', 'Pantry/Cupboard'),
        ('Counter', 'Counter'),
        ('Spice Rack', 'Spice Rack'),
        ('Wine Rack', 'Wine Rack'),
        ('Basement', 'Basement/Cellar'),
        ('Garage', 'Garage')
    ], validators=[Optional()])
    
    expiry_date = DateField('Expiry Date', validators=[Optional()])
    cost_per_unit = FloatField('Cost per Unit', validators=[Optional(), NumberRange(min=0)])
    last_purchased = DateField('Last Purchased', validators=[Optional()], default=date.today)
    
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Update Item')


class AddPantryItemForm(PantryItemForm):
    """Form for adding new pantry items"""
    submit = SubmitField('Add to Pantry')


class PantryQuickAddForm(FlaskForm):
    """Quick form for adding pantry items"""
    name = StringField('Item Name', validators=[DataRequired(), Length(min=1, max=100)])
    quantity = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0)], default=1.0)
    unit = SelectField('Unit', choices=[
        ('units', 'Units'),
        ('kg', 'Kg'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('ml', 'mL'),
        ('pieces', 'Pieces')
    ], default='units')
    
    submit = SubmitField('Quick Add')


class ShoppingListForm(FlaskForm):
    """Form for manually adding shopping list items"""
    item_name = StringField('Item Name', validators=[DataRequired(), Length(min=1, max=100)])
    quantity_needed = FloatField('Quantity Needed', validators=[DataRequired(), NumberRange(min=0.1)])
    unit = SelectField('Unit', choices=[
        ('units', 'Units'),
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('ml', 'Milliliters'),
        ('lbs', 'Pounds'),
        ('oz', 'Ounces'),
        ('pieces', 'Pieces'),
        ('cans', 'Cans'),
        ('bottles', 'Bottles')
    ], validators=[DataRequired()])
    
    category = StringField('Category', validators=[Optional(), Length(max=50)])
    priority = SelectField('Priority', choices=[
        (1, 'Urgent'),
        (2, 'High'),
        (3, 'Medium'),
        (4, 'Low'),
        (5, 'When Convenient')
    ], coerce=int, default=3)
    
    estimated_cost = FloatField('Estimated Cost', validators=[Optional(), NumberRange(min=0)])
    store_section = SelectField('Store Section', choices=[
        ('', 'Not Specified'),
        ('Produce', 'Produce'),
        ('Dairy', 'Dairy'),
        ('Meat', 'Meat & Seafood'),
        ('Frozen', 'Frozen Foods'),
        ('Pantry', 'Pantry/Dry Goods'),
        ('Beverages', 'Beverages'),
        ('Snacks', 'Snacks'),
        ('Health', 'Health & Beauty'),
        ('Household', 'Household Items')
    ], validators=[Optional()])
    
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=200)])
    
    submit = SubmitField('Add to Shopping List')


class BatchUpdateForm(FlaskForm):
    """Form for batch updating pantry items"""
    action = SelectField('Action', choices=[
        ('add_quantity', 'Add Quantity'),
        ('subtract_quantity', 'Subtract Quantity'),
        ('set_quantity', 'Set Quantity'),
        ('mark_expired', 'Mark as Expired'),
        ('update_location', 'Update Storage Location')
    ], validators=[DataRequired()])
    
    quantity_change = FloatField('Quantity Change', validators=[Optional(), NumberRange(min=0)])
    new_location = SelectField('New Storage Location', choices=[
        ('Fridge', 'Refrigerator'),
        ('Freezer', 'Freezer'),
        ('Pantry', 'Pantry/Cupboard'),
        ('Counter', 'Counter'),
        ('Spice Rack', 'Spice Rack')
    ], validators=[Optional()])
    
    reason = StringField('Reason for Change', validators=[Optional(), Length(max=100)], 
                        default='Batch update')
    
    submit = SubmitField('Apply Changes')
