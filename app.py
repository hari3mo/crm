from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_login import UserMixin, login_user, logout_user, current_user, login_required, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from dotenv import load_dotenv
import datetime
import json
import os

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from openai import OpenAI

import pandas as pd
import numpy as np

# Forms
from forms import LoginForm, SearchForm, UserForm, PasswordForm, FileForm, \
    UserUpdateForm, AccountForm, LeadForm, OpportunityForm, TextForm, \
    AdminUpdateForm, GenerateForm, LeadUpdateForm, OpportunityUpdateForm,\
    SaleForm

##############################################################################

app = Flask(__name__) 

# Load environment variables
load_dotenv()

# MySQL database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('MYSQL_URI')

# Secret key
app.config['SECRET_KEY'] = '9b2a012a1a1c425a8c86'

# Uploads folder
app.config['UPLOAD_FOLDER'] = 'static/files'

# Remember me duration
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=3)

# Set session timeout duration
app.permanent_session_lifetime = timedelta(minutes=30)

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)
engine = create_engine(os.getenv('MYSQL_URI')).connect() 

# Initiallize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = ""
login_manager.login_message_category = "danger"

@login_manager.user_loader
def load_user(user_id):
    try:
        return Users.query.get(int(user_id))
    except:
        return redirect(url_for('login'))
    # return Users.query.filter_by(UserID=user_id).first()

##############################################################################

# Routes

# Admin


# Login
@app.route('/login/', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = None
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = Users.query.filter_by(Email=form.email.data).first()
        except:
            return redirect(url_for('index'))
        # User exists
        if user:
            admin = None
            remember =None 
            remember = form.remember.data
            remember = True if remember else False
            if user.verify_password(form.password.data):
                login_user(user, remember=remember)
                # Check if user is an admin
                admin = Admins.query.filter_by(User=current_user.Email).first()
                session['admin'] = True if admin else False
                # session['image'] = str(current_user.Client.Image)
                flash('Successfully logged in.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Incorrect password.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('User does not exist.', 'danger')
            return redirect(url_for('login'))
        
    for fieldName, errorMessages in form.errors.items():
        for err in errorMessages:
            flash(err, 'danger')       
    return render_template('login.html', form=form)

# Sign up
@app.route('/signup/', methods=['POST', 'GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = UserForm()
    user = None
    client = None
    if form.validate_on_submit():
        user = Users.query.filter_by(Email=form.email.data).first()
        # User already exists
        if user is None:
            client = Clients.query.filter_by(License=form.license.data).first()
            # Invalid license key
            if client:
                # Hash password
                hashed_password = generate_password_hash(form.password.data, 'scrypt')
                        
                # Grab max id
                id = None
                id = Users.query.order_by(Users.UserID.desc()).first()
            
                if id is None:
                        id = 100
                else:
                    id = id.UserID + 1
                
                new_user = Users(UserID=id,
                                FirstName=form.first_name.data,
                                LastName=form.last_name.data,
                                Email=form.email.data,
                                License=client.License,
                                PasswordHash=hashed_password,
                                ClientID=client.ClientID)
                
                db.session.add(new_user)
                db.session.commit()
                flash('User created successfully. Please log in.', 'success')
                return redirect(url_for('login'))
            
            else:
                flash('Invalid license key.', 'danger')
                return redirect(url_for('signup'))
        else:
            flash('User already exists.', 'danger')
            return redirect(url_for('signup'))
    
    for fieldName, errorMessages in form.errors.items():
        for err in errorMessages:
            flash(err, 'danger')
            
    return render_template('signup.html', form=form)

# Logout function
@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('login'))

# Analytics


# Accounts list
@app.route('/accounts/list/')
@login_required
def accounts_list():
    accounts = None

    accounts = Accounts.query.filter_by(ClientID=current_user.ClientID)
    
    # Sort options    
    sort = request.args.get('sort')
    order = request.args.get('order')
    if sort:
        if sort == 'revenue':
            if order == 'asc':
                accounts = accounts.order_by(Accounts.CompanyRevenue)
            else:
                accounts = accounts.order_by(Accounts.CompanyRevenue.desc())
        if sort == 'head_count':
            if order == 'asc':
                accounts = accounts.order_by(Accounts.EmployeeHeadCount)
            else:
                accounts = accounts.order_by(Accounts.EmployeeHeadCount.desc())
    else:
        accounts = accounts.order_by(Accounts.AccountID.desc())
    
    # Filter query
    industries = db.session.query(Accounts.CompanyIndustry).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.CompanyIndustry.isnot(None)).all()
    industries = sorted([str(industry).strip('(').strip(')').strip(',').strip("'").strip('"') for industry in industries])
    industry = request.args.get('industry')
    if industry:
        accounts = accounts.filter_by(CompanyIndustry=industry)
    
    types = db.session.query(Accounts.CompanyType).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.CompanyType.isnot(None)).all()
    types = sorted([str(type).strip('(').strip(')').strip(',').strip("'").strip('"') for type in types])
    type = request.args.get('type')
    if type:
        accounts = accounts.filter_by(CompanyType=type)
    
    countries = db.session.query(Accounts.Country).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.Country.isnot(None)).all()
    countries = sorted([str(country).strip('(').strip(')').strip(',').strip("'").strip('"') for country in countries])
    country = request.args.get('country')
    if country:
        accounts = accounts.filter_by(Country=country)
    
    cities = db.session.query(Accounts.City).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.City.isnot(None)).all()
    cities = sorted([str(city).strip('(').strip(')').strip(',').strip("'").strip('"') for city in cities])
    city = request.args.get('city')
    if city:
        accounts = accounts.filter_by(City=city)
    
    timezones = db.session.query(Accounts.Timezone).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.Timezone.isnot(None)).all()
    timezones = sorted([str(timezone).strip('(').strip(')').strip(',').strip("'").strip('"') for timezone in timezones])
    timezone = request.args.get('timezone')
    if timezone:
        accounts = accounts.filter_by(Timezone=timezone)
    
    
    return render_template('accounts/accounts_list.html', accounts=accounts,
        industries=industries, types=types, countries=countries, cities=cities,
        timezones=timezones)

# Leads list
@app.route('/leads/list/')
def leads_list():
    leads = None
    leads = Leads.query.filter_by(ClientID=current_user.ClientID)
    
    # Filter query
    positions = db.session.query(Leads.Position).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Leads.Position.isnot(None)).all()
    positions = sorted([str(position).strip('(').strip(')').strip(',').strip("'").strip('"') for position in positions])
    position = request.args.get('position')
    if position:
        leads = leads.filter_by(Position=position)
        
    companies = db.session.query(Leads.CompanyName).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Leads.CompanyName.isnot(None)).all()
    companies = sorted([str(company).strip('(').strip(')').strip(',').strip("'").strip('"') for company in companies])
    company = request.args.get('company')
    if company:
        leads = leads.filter_by(CompanyName=company)
    
    return render_template('leads/leads_list.html', leads=leads, companies=companies,
                           positions=positions)

# Import accounts
@app.route('/accounts/import/', methods=['GET', 'POST'])
@login_required
def import_accounts():
    form = FileForm()
    filename = None
    if form.validate_on_submit():        
        file = form.file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if filename.split('.')[-1] != 'csv':
            flash('Import failed. Please upload a .csv file.', 'danger')
            return redirect(url_for('import_accounts'))
        
        try:        
            # Rename function
            while os.path.exists(filepath):
                filename = filename.split('.')[0] + ' copy.csv'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)                        
            
            file.save(filepath)
            
            df = pd.read_csv('static/files/{filename}'.format(filename=filename))
            # Replace NaN with None
            df = df.replace({np.nan: None})
            
            df = df.rename(columns={df.columns[0]: 'CompanyName',
                                    df.columns[1]: 'CompanyRevenue',
                                    df.columns[2]: 'EmployeeHeadCount',
                                    df.columns[3]: 'CompanyIndustry',
                                    df.columns[4]: 'CompanySpecialties',
                                    df.columns[5]: 'CompanyType',
                                    df.columns[6]: 'Country',
                                    df.columns[7]: 'City',
                                    df.columns[8]: 'Timezone'})
            
            # Grab max id
            id = Accounts.query.order_by(Accounts.AccountID.desc()).first()
        
            if id is None:
                    id = 1000
            else:
                id = id.AccountID + 10
                
            for index, row in df.iterrows():
                dct = row.to_dict()
                dct.update({'AccountID': id, 'ClientID': current_user.ClientID})
                id += 10
                account = Accounts(**dct)
                db.session.add(account)
                
            db.session.commit()
            os.remove(filepath)        
            flash('Accounts import successful.', 'success')
            return redirect(url_for('accounts_list'))    
                
        except:
            db.session.rollback()
            flash('Import failed. Please ensure .csv file is ordered as \
                follows: Company Name, Company Revenue, Employee Head Count, \
                Company Industry, Company Specialties, Company Type, Country, \
                City, Timezone.', 'danger')
            return redirect(url_for('import_accounts'))
        
    return render_template('accounts/import_accounts.html', form=form)

# Import leads
@app.route('/leads/import/', methods=['GET', 'POST'])
def import_leads():
    form = FileForm()
    filename = None
    if form.validate_on_submit():     
        file = form.file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            if filename.split('.')[-1] != 'csv':
                flash('Import failed. Please upload a .csv file.')
                return redirect(url_for('import_leads'))
                
            # Rename function
            while os.path.exists(filepath):
                filename = filename.split('.')[0] + ' copy.csv'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)                        
            
            file.save(filepath)
            
            df = pd.read_csv('static/files/{filename}'.format(filename=filename))
            
            df = df.rename(columns={df.columns[0]: 'CompanyName',
                                    df.columns[1]: 'Position',
                                    df.columns[2]: 'FirstName',
                                    df.columns[3]: 'LastName',
                                    df.columns[4]: 'Email'})
            
            accounts_df = pd.read_sql(db.session.query(Accounts).filter(Accounts.ClientID == current_user.ClientID).statement, con=engine)
            df = pd.merge(df, accounts_df[['AccountID', 'CompanyName', 'ClientID']], on='CompanyName')
            # Replace NaN with None
            df = df.replace({np.nan: None})
            
            # Grab max id
            id = Leads.query.order_by(Leads.LeadID.desc()).first()
        
            if id is None:
                    id = 10000
            else:
                id = id.LeadID + 50
            
            for index, row in df.iterrows():
                dct = row.to_dict()
                dct.update({'LeadID': id})
                id += 50
                lead = Leads(**dct)
                db.session.add(lead)

            
            db.session.commit() 
            os.remove(filepath)        
            flash('Import successful.', 'success')
            return redirect(url_for('leads_list'))    

            
        except:
            db.session.rollback()
            flash('Import failed. Please ensure .csv file is ordered as \
                follows: Company Name, Position, First Name, Last Name, \
                    Email', 'danger')
            return redirect(url_for('import_leads'))
        
    return render_template('leads/import_leads.html', form=form)

# New Account
@app.route('/accounts/new/', methods=['GET', 'POST'])
@login_required
def new_account():
    form = AccountForm()
    try:
        if form.validate_on_submit():
            # Grab max id
            id = Accounts.query.order_by(Accounts.AccountID.desc()).first()
            
            if id is None:
                id = 1000
            else:
                id = id.AccountID + 10
                
            account = Accounts(AccountID=id,
                            CompanyName=form.company_name.data, 
                            CompanyRevenue=form.company_revenue.data, 
                            EmployeeHeadCount=form.employee_head_count.data,
                            CompanySpecialties=form.company_specialties.data, 
                            CompanyIndustry=form.company_industry.data,
                            CompanyType = form.company_type.data, 
                            Country=form.country.data, 
                            City=form.city.data, 
                            Timezone=form.timezone.data,
                            ClientID=current_user.ClientID)
            
            db.session.add(account)
            db.session.commit()
            
            flash('Account added successfully.', 'success')
            return redirect(url_for('accounts_list'))
        
    except:
        flash('Error adding account.', 'danger')
        return redirect(url_for('new_account'))
           
    return render_template('accounts/new_account.html', form=form)

# New lead
@app.route('/leads/new/', methods=['GET', 'POST'])
def new_lead():
    form = LeadForm()
    if form.validate_on_submit():
        account = None
        
        if form.company.data.isnumeric():
            account = Accounts.query.filter_by(ClientID=current_user.ClientID)\
                .filter_by(AccountID=form.company.data).first()
        else:
            account = Accounts.query.filter_by(ClientID=current_user.ClientID)\
                .filter_by(CompanyName=form.company.data).first()        
        
        if account:
            # Grab max id
            id = Leads.query.order_by(Leads.LeadID.desc()).first()
            
            if id is None:
                id = 10000
            else:
                id = id.LeadID + 50
                
            if account:
                lead = Leads(LeadID=id,
                            AccountID=account.AccountID,
                            ClientID=current_user.ClientID,
                            Position=form.position.data,
                            FirstName=form.first_name.data,
                            LastName=form.last_name.data,
                            Email=form.email.data,
                            CompanyName=account.CompanyName)
                
                db.session.add(lead)
                db.session.commit()
                flash('Lead added successfully.', 'success')
                return redirect(url_for('leads_list'))
        
        else:
            flash('Account not found.', 'danger')
            return redirect(url_for('new_lead'))
    
    return render_template('leads/new_lead.html', form=form)

# Update lead
@app.route('/leads/update/<int:id>', methods=['GET', 'POST'])
def lead(id):
    lead = Leads.query.get_or_404(id)
    form = LeadUpdateForm()
    return render_template('leads/lead.html', lead=lead, form=form)

# Update account
@app.route('/accounts/update/<int:id>', methods=['GET', 'POST'])
@login_required
def account(id):
    form = AccountForm()
    account = Accounts.query.get_or_404(id)
    form.company_specialties.data = account.CompanySpecialties
    if form.validate_on_submit():

        account.CompanyName = form.company_name.data
        account.CompanyRevenue = form.company_revenue.data
        account.EmployeeHeadCount = form.employee_head_count.data
        account.CompanySpecialties = form.company_specialties.data
        account.CompanyType = form.company_type.data
        account.Country = form.country.data
        account.City = form.city.data
        account.Timezone = form.timezone.data
        
        try:
            db.session.commit()
            flash('Account updated successfully.', 'success')
            return redirect(url_for('account', id=id))
        
        except:
            flash('Account update failed.', 'danger')
            return redirect(url_for('account', id=id))

        
    return render_template('accounts/account.html', form=form, account=account, id=id)    

# Delete account
@app.route('/accounts/delete/<int:id>')
@login_required
def delete_account(id):
    account = Accounts.query.get_or_404(id)
    try:
        db.session.delete(account)
        db.session.commit()
        flash('Account deleted successfully.', 'success')
        return redirect(url_for('accounts_list'))
    
    except:
        flash('Error deleting account.', 'danger')
        return redirect(url_for('accounts_list'))
    
# Delete lead
@app.route('/leads/delete/<int:id>')
@login_required
def delete_lead(id):
    lead = Leads.query.get_or_404(id)
    try:
        db.session.delete(lead)
        db.session.commit()
        flash('Lead deleted successfully.', 'success')
        return redirect(url_for('leads_list'))
    
    except:
        flash('Error deleting lead.', 'danger')
        return redirect(url_for('leads_list'))

# Clear accounts
@app.route('/accounts/clear/')
@login_required
def clear_accounts():
    Accounts.query.delete()
    db.session.commit()
    flash('Accounts cleared successfully.', 'success')
    return redirect(url_for('accounts_list'))

# Clear leads
@app.route('/leads/clear/')
@login_required
def clear_leads():
    Leads.query.delete()
    db.session.commit()
    flash('Leads cleared successfully.', 'success')
    return redirect(url_for('leads_list'))


# Invalid URL
@app.errorhandler(404)
def page_not_foredid(e):
    return redirect(url_for('index'))

##############################################################################

# Models

# Clients model
class Clients(db.Model):
    __tablename__ = 'Clients'
    ClientID = db.Column(db.Integer, primary_key=True)
    Client = db.Column(db.String(50), nullable=False, unique=True)
    License = db.Column(db.String(20), nullable=False, unique=True)
    Image = db.Column(db.String(255), unique=True)
    ValidFrom = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    ValidTo = db.Column(db.Date)
    
    # References
    User = db.relationship('Users', backref='Client')
    Account = db.relationship('Accounts', backref='Client')
    Lead = db.relationship('Leads', backref='Clients')
    Opportunity = db.relationship('Opportunities', backref='Client')
    Sale = db.relationship('Sales', backref='Client')
    
# Accounts model
class Accounts(db.Model):
    __tablename__ = 'Accounts'
    AccountID = db.Column(db.Integer, primary_key=True)
    CompanyName = db.Column(db.String(100), nullable=False)
    CompanyRevenue = db.Column(db.Integer, nullable=False)
    EmployeeHeadCount = db.Column(db.Integer, nullable=False)
    CompanyIndustry = db.Column(db.String(100))
    CompanySpecialties = db.Column(db.Text)
    CompanyType = db.Column(db.String(50))
    Country = db.Column(db.String(50), nullable=False)
    City = db.Column(db.String(50))
    Timezone = db.Column(db.String(50))
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    
    # References
    Leads = db.relationship('Leads', backref='Account')
    Opportunities = db.relationship('Opportunities', backref='Account')
    
# Leads model
class Leads(db.Model):
    __tablename__ = 'Leads'
    LeadID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AccountID = db.Column(db.Integer, db.ForeignKey(Accounts.AccountID)) # Foreign key to AccountID
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    Position = db.Column(db.String(75), nullable=False)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(50), unique=True)
    CompanyName =  db.Column(db.String(100), nullable=False)
    
    # References
    Opportunities = db.relationship('Opportunities', backref='Lead')


# Opportunities model    
class Opportunities(db.Model):
    __tablename__ = 'Opportunities'
    OpportunityID = db.Column(db.Integer, primary_key=True)
    AccountID = db.Column(db.Integer, db.ForeignKey(Accounts.AccountID)) # Foreign Key to AccountID
    LeadID = db.Column(db.Integer, db.ForeignKey(Leads.LeadID)) # Foreign key to LeadID
    Opportunity = db.Column(db.Text)
    Value = db.Column(db.String(255))
    Stage = db.Column(db.String(100))
    CreationDate = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    CloseDate = db.Column(db.Date)
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID

    # References
    Sale = db.relationship('Sales', backref='Opportunity')

# Sales model
class Sales(db.Model):
    __tablename__ = 'Sales'
    SaleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OpportunityID = db.Column(db.Integer, db.ForeignKey(Opportunities.OpportunityID)) # Foreign key to OpportunityID
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    SaleAmount = db.Column(db.Integer)
    SalesRep = db.Column(db.String(50))
    SaleDate = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))

# Users model
class Users(db.Model, UserMixin):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Email = db.Column(db.String(50), unique=True, nullable=False)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)
    License = db.Column(db.String(20), nullable=False)
    ValidFrom = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    ValidTo = db.Column(db.Date)
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')
    
    @password.setter
    def password(self, password):
        self.PasswordHash = generate_password_hash(password)
        
    def verify_password(self, password):
        return check_password_hash(self.PasswordHash, password)  
    
    # Override get_id to return the correct identifier
    def get_id(self):
        return str(self.UserID)

    @property
    def is_authenticated(self):
        return True  # Assuming the presence of a valid session tokenp
    
# Admins model
class Admins(db.Model):
    __tablename__ = 'Admins'
    User = db.Column(db.String(50), primary_key=True)

##############################################################################

if __name__ == "__main__":
    app.run(debug=True)
    