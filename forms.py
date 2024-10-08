from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField,\
    IntegerField, FileField, TextAreaField, SelectField, BooleanField, ValidationError
from flask_wtf.file import FileRequired
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

# Forms
    
# Account form
class AccountForm(FlaskForm):
    company_name = StringField('Company Name:*', validators=[DataRequired()])
    company_revenue = IntegerField('Revenue (millions):*', validators=[DataRequired()])
    employee_head_count = IntegerField('Head Count:*', validators=[DataRequired()])
    company_specialties = TextAreaField('Company Specialties:')
    company_industry = StringField('Company Industry:')
    company_type = StringField('Company Type:')
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
    country = StringField('Country:*', validators=[DataRequired()])
    city = StringField('City:')
    timezone = StringField('Timezone:')
    submit = SubmitField('Submit')
    
    # email = EmailField('Email:', validators=[DataRequired(), Email()])

# Lead form
class LeadForm(FlaskForm):
    first_name = StringField('First Name:', validators=[DataRequired()])
    last_name = StringField('Last Name:', validators=[DataRequired()])
    email  = EmailField('Email:', validators=[Optional(), Email()])
    position = StringField('Position:', validators=[DataRequired()])
    company = StringField('Account:', validators=[DataRequired()])
    # status = SelectField('Status:', choices=[('Open', 'Open'), ('Closed', 'Closed'),
    #                                          ('Converted', 'Converted')])
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
    submit = SubmitField('Submit')
    
# Lead update form
class LeadUpdateForm(FlaskForm):
    first_name = StringField('First Name:', validators=[DataRequired()])
    last_name = StringField('Last Name:', validators=[DataRequired()])
    email  = EmailField('Email:', validators=[Optional(), Email()])
    position = StringField('Position:', validators=[DataRequired()])
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
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
    lead = SelectField('Lead:', coerce=int, validators=[DataRequired()])
    opportunity = TextAreaField('Opportunity:', validators=[DataRequired()])
    value = IntegerField('Value:', validators=[DataRequired()])
    stage = SelectField('Stage:', choices=[('In Process', 'In Process'), ('Proposals', 'Proposals'),\
        ('Negotiations', 'Negotiations'), ('Won', 'Won'), ('Loss', 'Loss')])
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
    submit = SubmitField('Submit')
    
# Opportunity update form
class OpportunityUpdateForm(FlaskForm):
    lead = SelectField('Lead:', coerce=int, validators=[DataRequired()])
    opportunity = TextAreaField('Opportunity:', validators=[DataRequired()])
    value = IntegerField('Value:', validators=[DataRequired()])
    stage = SelectField('Stage:', choices=[('In Process', 'In Process'), ('Proposals', 'Proposals'),\
        ('Negotiations', 'Negotiations'), ('Won', 'Won'), ('Loss', 'Loss')])
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
    submit = SubmitField('Submit')
    
# Sale form
class SaleForm(FlaskForm):
    opportunity = IntegerField('Opportunity:', validators=[DataRequired()])
    value = IntegerField('Value:', validators=[DataRequired()])
    stage = SelectField('Stage:', choices=[('Prospecting', 'Prospecting'), ('Qualification', 'Qualification'),\
        ('Proposal', 'Proposal'), ('Negotiation', 'Negotiation'), ('Won', 'Won'), ('Loss', 'Loss')])
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
    submit = SubmitField('Submit')

# Sale form
class SaleUpdateForm(FlaskForm):
    value = IntegerField('Value:', validators=[DataRequired()])
    stage = SelectField('Stage:', choices=[('Prospecting', 'Prospecting'), ('Qualification', 'Qualification'),\
        ('Proposal', 'Proposal'), ('Negotiation', 'Negotiation'), ('Won', 'Won'), ('Loss', 'Loss')])
    owner = SelectField('Owner:', coerce=int, validators=[Optional()])
    submit = SubmitField('Submit')

# File form
class FileForm(FlaskForm):
    file = FileField('File', validators=[FileRequired()])
    submit = SubmitField('Submit')
 

# Login form
class LoginForm(FlaskForm):
    email = EmailField('Email:', validators=[DataRequired(), Email()])
    password = PasswordField('Password:', validators=[DataRequired()])
    remember = BooleanField('Remember me')
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

# Interaction form
class InteractionForm(FlaskForm):
    interaction = TextAreaField('Interaction:', validators=[DataRequired()])
    submit = SubmitField()
    
# Generate leads list form
class GenerateLeadsForm(FlaskForm):
    submit = SubmitField('Submit')

# Generate sales script form
class GenerateScriptForm(FlaskForm):
    lead_id = IntegerField('LeadID:', validators=[DataRequired()])
    submit = SubmitField('Submit')

##############################################################################

# Test forms

# Password form (testing)
class PasswordForm(FlaskForm):
    hashed_password = StringField('Hashed Password:', validators=[DataRequired()])
    password = StringField('Password:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
# Text field form (testing)
class TextForm(FlaskForm):
    text = TextAreaField('Text:')
    submit = SubmitField('Submit')

