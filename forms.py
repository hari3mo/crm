from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField,\
    IntegerField, FileField, TextAreaField, SelectField, BooleanField, ValidationError
from flask_wtf.file import FileRequired
from wtforms.validators import DataRequired, Email, EqualTo, Length


# Forms
    
# Account form
class AccountForm(FlaskForm):
    company_name = StringField('Company Name:*', validators=[DataRequired()])
    company_revenue = IntegerField('Revenue:*', validators=[DataRequired()])
    employee_head_count = IntegerField('Head Count:*', validators=[DataRequired()])
    company_specialties = StringField('Company Specialties:')
    company_industry = StringField('Company Industry:')
    company_type = StringField('Company Type:')
    country = StringField('Country:*', validators=[DataRequired()])
    city = StringField('City:')
    timezone = StringField('Timezone:')
    submit = SubmitField('Submit')
    
    # email = EmailField('Email:', validators=[DataRequired(), Email()])

# Lead form
class LeadForm(FlaskForm):
    first_name = StringField('First Name:', validators=[DataRequired()])
    last_name = StringField('Last Name:', validators=[DataRequired()])
    email  = StringField('Email:', validators=[DataRequired(), Email()])
    position = StringField('Position:', validators=[DataRequired()])
    company = StringField('Company Name or AccountID:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
# Lead update form
class LeadUpdateForm(FlaskForm):
    first_name = StringField('First Name:', validators=[DataRequired()])
    last_name = StringField('Last Name:', validators=[DataRequired()])
    email  = StringField('Email:', validators=[DataRequired(), Email()])
    position = StringField('Position:', validators=[DataRequired()])
    submit = SubmitField('Submit')

# User form
class UserForm(FlaskForm):
    email = EmailField('Email:', validators=[DataRequired(), Email()])
    first_name = StringField('First Name:', validators=[DataRequired()])
    last_name = StringField('Last Name:', validators=[DataRequired()])
    license = StringField('License Key:', validators=[DataRequired(),
                                            Length(min=20, max=20, 
                                                    message='License key must be\
                                                20 characters.')])
    password = PasswordField('Password:', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password:', 
                                     validators=[DataRequired(), 
                                                EqualTo('password', 
                                                        message='Passwords do not match.')])
    submit = SubmitField('Submit')
    
# Opportunity form
class OpportunityForm(FlaskForm):
    account = StringField('Account:', validators=[DataRequired()])
    lead = SelectField('Lead:', coerce=int, validate_choice=False, validators=[DataRequired()])
    opportunity = StringField('Opportunity:', validators=[DataRequired()])
    value = StringField('Value:', validators=[DataRequired()])
    stage = StringField('Stage:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
# Opportunity update form
class OpportunityUpdateForm(FlaskForm):
    lead = SelectField('Lead:', coerce=int, validate_choice=False, validators=[DataRequired()])
    opportunity = StringField('Opportunity:', validators=[DataRequired()])
    value = StringField('Value:', validators=[DataRequired()])
    stage = StringField('Stage:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
# Sale form
class SaleForm(FlaskForm):
    sale_amount = IntegerField('Sale Amount:*', validators=[DataRequired()])
    sales_rep = StringField('Sales Representative:')
    submit = SubmitField('Submit')

# File form
class FileForm(FlaskForm):
    file = FileField('File', validators=[FileRequired()])
    submit = SubmitField('Submit')
 
# Password form
class PasswordForm(FlaskForm):
    hashed_password = StringField('Hashed Password:', validators=[DataRequired()])
    password = StringField('Password:', validators=[DataRequired()])
    submit = SubmitField('Submit')

# Login form
class LoginForm(FlaskForm):
    email = EmailField('Email:', validators=[DataRequired(), Email()])
    password = PasswordField('Password:', validators=[DataRequired()])
    submit = SubmitField('Login')
    
# Search form
class SearchForm(FlaskForm):
    search = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Submit')

# User update form
class UserUpdateForm(FlaskForm):
    email = EmailField('Email:', validators=[Email()])
    password = PasswordField('Old Password:*', validators=[DataRequired()])
    new_password = PasswordField('New Password:')
    confirm_password = PasswordField('Confirm Password:', 
                                     validators=[EqualTo('new_password', 
                                                         message='Passwords do not match.')])
    submit = SubmitField('Submit')
    
# Admin user update form
class AdminUpdateForm(FlaskForm):
    email = EmailField('Email:', validators=[Email()])
    first_name = StringField('First Name:', validators=[DataRequired()])
    last_name = StringField('Last Name:', validators=[DataRequired()])
    password = PasswordField('New Password:')
    confirm_password = PasswordField('Confirm Password:', 
                                     validators=[EqualTo('password', 
                                                         message='Passwords do not match.')])
    submit = SubmitField('Submit')
    
# Generate analytics form
class GenerateForm(FlaskForm):
    submit = SubmitField('Submit')

    
# Text field form
class TextForm(FlaskForm):
    text = TextAreaField('Text:')
    submit = SubmitField('Submit')

