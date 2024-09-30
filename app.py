from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_login import UserMixin, login_user, logout_user, current_user, login_required, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
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
from forms import LoginForm, SearchForm, UserForm, FileForm, \
    UserUpdateForm, AccountForm, LeadForm, OpportunityForm, \
    AdminUpdateForm, GenerateForm, LeadUpdateForm, OpportunityUpdateForm,\
    SaleForm, SaleUpdateForm, InteractionForm

##############################################################################
# Load environment variables
load_dotenv()

# Initialize app
app = Flask(__name__) 


# MySQL database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('MYSQL_URI')

# Secret key
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Uploads folder
app.config['UPLOAD_FOLDER'] = 'static/files'

# Remember me duration
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=3)

# Initialize cache
app.config['CACHE_TYPE'] = 'simple'
cache = Cache()
cache.init_app(app)

# Set default session timeout length
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
        # return Users.query.filter_by(UserID=user_id).first()
        return Users.query.get(int(user_id))
    except:
        return redirect(url_for('login'))
    
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
            remember = None 
            remember = form.remember.data
            remember = True if remember else False
            if user.verify_password(form.password.data):
                login_user(user, remember=remember)
                # Check if user is an admin
                admin = Admins.query.filter_by(User=current_user.Email).first()
                session['admin'] = True if admin else False
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
    leads = pd.read_sql_table(con=engine, table_name='Leads')
    accounts = pd.read_sql_table(con=engine, table_name='Accounts')
    accounts_count = accounts[accounts['CompanyRevenue'] > 0].shape[0]
    mean_revenue = float(round(accounts['CompanyRevenue'][accounts['CompanyRevenue'] > 0].mean(), ndigits=2))
    return render_template('index.html', leads=leads.shape[0], mean_revenue=mean_revenue)

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
    industries = sorted([industry.CompanyIndustry for industry in industries])
    industry = request.args.get('industry')
    if industry:
        accounts = accounts.filter_by(CompanyIndustry=industry)
    
    types = db.session.query(Accounts.CompanyType).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.CompanyType.isnot(None)).all()
    types = sorted([type.CompanyType for type in types])
    type = request.args.get('type')
    if type:
        accounts = accounts.filter_by(CompanyType=type)
    
    countries = db.session.query(Accounts.Country).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.Country.isnot(None)).all()
    countries = sorted([country.Country for country in countries])
    country = request.args.get('country')
    if country:
        accounts = accounts.filter_by(Country=country)
    
    cities = db.session.query(Accounts.City).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.City.isnot(None)).all()
    cities = sorted([city.City for city in cities])
    city = request.args.get('city')
    if city:
        accounts = accounts.filter_by(City=city)
    
    timezones = db.session.query(Accounts.Timezone).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.Timezone.isnot(None)).all()
    timezones = sorted([timezone.Timezone for timezone in timezones])
    timezone = request.args.get('timezone')
    if timezone:
        accounts = accounts.filter_by(Timezone=timezone)
    
    owners = db.session.query(Accounts.Owner).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Accounts.Owner.isnot(None)).all()
    owners = [owner.Owner for owner in owners]
    owners = Users.query.filter(Users.UserID.in_(owners)).order_by(Users.FirstName, Users.LastName).all()
    owner = request.args.get('owner')
    
    if owner:
        if owner == 'NA':
            accounts = accounts.filter(Accounts.Owner.is_(None))
        else:
            accounts = Accounts.query.filter_by(Owner=owner)
    
    return render_template('accounts/accounts_list.html', accounts=accounts.all(),
        industries=industries, types=types, owners=owners, countries=countries, 
        cities=cities, timezones=timezones)

# Leads list
@app.route('/leads/list/')
@login_required
def leads_list():
    leads = None
    leads = Leads.query.filter_by(ClientID=current_user.ClientID).order_by(Leads.LeadID.desc())
        
    # Filter query
    positions = db.session.query(Leads.Position).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Leads.Position.isnot(None)).all()
    positions = sorted([position.Position for position in positions])
    if '' in positions:
        positions.remove('')
    position = request.args.get('position')
    if position:
        leads = leads.filter_by(Position=position)
        
    companies = db.session.query(Accounts.CompanyName).join(Leads, Leads.AccountID == Accounts.AccountID)\
    .distinct().filter_by(ClientID=current_user.ClientID).filter(Accounts.CompanyName.isnot(None)).all()
    companies = sorted([company.CompanyName for company in companies])
    company = request.args.get('company')
    if company:
        leads = leads.join(Accounts, Leads.AccountID == Accounts.AccountID).filter(Accounts.CompanyName == company)
        
    cities = db.session.query(Accounts.City).join(Leads, Leads.AccountID == Accounts.AccountID)\
        .distinct().filter_by(ClientID=current_user.ClientID).filter(Accounts.City.isnot(None)).all()
    cities = sorted([city.City for city in cities])
    city = request.args.get('city')
    if city:
        leads = leads.join(Accounts, Leads.AccountID == Accounts.AccountID).filter(Accounts.City == city)

    status = request.args.get('status')
    if status:
        leads = leads.filter_by(Status=status)
    import logging
            
    owners = db.session.query(Leads.Owner).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Leads.Owner.isnot(None)).all()
    owners = [owner.Owner for owner in owners]
    owners = Users.query.filter(Users.UserID.in_(owners)).order_by(Users.FirstName, Users.LastName).all()
    owner = request.args.get('owner')
    if owner:
        if owner == 'NA':
            leads = leads.filter(Leads.Owner.is_(None))
        else:
            leads = Leads.query.filter_by(Owner=owner)
    
    follow_up = request.args.get('follow_up')
    if follow_up:
        if follow_up == 'True':
            leads = leads.filter_by(FollowUp=True)
        else:
            leads = leads.filter_by(FollowUp=False)
    
    return render_template('leads/leads_list.html', leads=leads.limit(20), companies=companies,
        positions=positions, cities=cities, owners=owners)


# Opportunities list
@app.route('/opportunities/opportunities_list/')
@login_required
def opportunities_list():
    opportunities = Opportunities.query.filter_by(ClientID=current_user.ClientID)\
        .order_by(Opportunities.OpportunityID.desc())
    
    accounts = db.session.query(Accounts.CompanyName).join(Opportunities, Opportunities.AccountID == Accounts.AccountID)\
                .distinct().filter_by(ClientID=current_user.ClientID).filter(Accounts.CompanyName.isnot(None)).all()
    accounts = sorted([account.CompanyName for account in accounts])
    account = request.args.get('account')
    if account:
        opportunities = opportunities.join(Accounts, Opportunities.AccountID == Accounts.AccountID)\
            .filter(Accounts.CompanyName == account)    
    
    sort = request.args.get('sort')
    order = request.args.get('order')
    if sort == 'value':
        if order == 'asc':
            opportunities = opportunities.order_by(Opportunities.Value.asc())
        else:
            opportunities = opportunities.order_by(Opportunities.Value.desc())
    if sort == 'date':
        if order == 'asc':
            opportunities = opportunities.order_by(Opportunities.DateCreated.asc())
        else:
            opportunities = opportunities.order_by(Opportunities.DateCreated.desc())
    else:
        opportunities = opportunities.order_by(Opportunities.OpportunityID.desc())
        
    stage = request.args.get('stage')
    if stage:
        opportunities = opportunities.filter_by(Stage=stage)
      
    owners = db.session.query(Opportunities.Owner).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Opportunities.Owner.isnot(None)).all()
    owners = [owner.Owner for owner in owners]
    owners = Users.query.filter(Users.UserID.in_(owners)).order_by(Users.FirstName, Users.LastName).all()
    owner = request.args.get('owner')
    
    if owner:
        if owner == 'NA':
            opportunities = opportunities.filter(Opportunities.Owner.is_(None))
        else:
            opportunities = Opportunities.query.filter_by(Owner=owner)
        
    return render_template('opportunities/opportunities_list.html', opportunities=opportunities.all(),
                           accounts=accounts, owners=owners)

# Sales list 
@app.route('/sales/list/')
@login_required
def sales_list():
    sales = Sales.query.filter_by(ClientID=current_user.ClientID).order_by(Sales.SaleID.desc())
        
    accounts = db.session.query(Accounts.CompanyName).join(Sales, Sales.AccountID == Accounts.AccountID)\
                .distinct().filter_by(ClientID=current_user.ClientID).filter(Accounts.CompanyName.isnot(None)).all()
    accounts = sorted([account.CompanyName for account in accounts])
    account = request.args.get('account')
    if account:
        sales = sales.join(Accounts, Sales.AccountID == Accounts.AccountID)\
            .filter(Accounts.CompanyName == account)
            
    sort = request.args.get('sort')
    order = request.args.get('order')
    if sort == 'value':
        if order == 'asc':
            sales = sales.order_by(Sales.Value.asc())
        else:
            sales = sales.order_by(Sales.Value.desc())
    if sort == 'date':
        if order == 'asc':
            sales = sales.order_by(Sales.DateCreated.asc())
        else:
            sales = sales.order_by(Sales.DateCreated.desc())
    else:
        sales = sales.order_by(Sales.OpportunityID.desc())    
        
    stage = request.args.get('stage')
    if stage:
        opportunities = opportunities.filter_by(Stage=stage)
    
    owners = db.session.query(Sales.Owner).filter_by(ClientID=current_user.ClientID)\
        .distinct().filter(Sales.Owner.isnot(None)).all()
    owners = [owner.Owner for owner in owners]
    owners = Users.query.filter(Users.UserID.in_(owners)).order_by(Users.FirstName, Users.LastName).all()
    owner = request.args.get('owner')
    
    if owner:
        if owner == 'NA':
            sales = sales.filter(Sales.Owner.is_(None))
        else:
            sales = Sales.query.filter_by(Owner=owner)
    
    
    return render_template('sales/sales_list.html', sales=sales.all(), accounts=accounts,
                           owners=owners)

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
            # while os.path.exists(filepath):
            #     filename = filename.split('.')[0] + ' copy.csv'
            #     filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)                        
            
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
            
            df = df.assign(ClientID=current_user.ClientID, 
                           CreatedBy=current_user.Email,
                           Owner=None,
                           DateCreated=datetime.datetime.now(datetime.timezone.utc))
            
            # Grab max id
            id = Accounts.query.order_by(Accounts.AccountID.desc()).first()
        
            if id is None:
                    id = 1000
            else:
                id = id.AccountID + 10
                
                
            df['AccountID'] = np.arange(id, id + 10*df.shape[0], 10)
            df.to_sql('Accounts', con=engine, if_exists='append', index=False)
            
            # Convert DataFrame to a list of dictionaries
            # records = df.to_dict(orient='records')

            # Iterate over the list of dictionaries
            # for dct in records:
            #     dct.update({'AccountID': id})
            #     id += 10
            #     account = Accounts(**dct)
            #     db.session.add(account)
            
            # Iterate over rows method
            # for index, row in df.iterrows():
            #     dct = row.to_dict()
            #     dct.update({'AccountID': id})
            #     id += 10
            #     account = Accounts(**dct)
            #     db.session.add(account)
                
            # db.session.commit()
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
@login_required
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
            # while os.path.exists(filepath):
            #     filename = filename.split('.')[0] + ' copy.csv'
            #     filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)                        
            
            file.save(filepath)
            
            df = pd.read_csv('static/files/{filename}'.format(filename=filename))
            
            df = df.rename(columns={df.columns[0]: 'CompanyName',
                                    df.columns[1]: 'Position',
                                    df.columns[2]: 'FirstName',
                                    df.columns[3]: 'LastName',
                                    df.columns[4]: 'Email'})
            
            accounts_df = pd.read_sql(db.session.query(Accounts).filter_by(ClientID=current_user.ClientID).statement, con=engine)
            df = pd.merge(df, accounts_df[['AccountID', 'CompanyName', 'ClientID']], on='CompanyName')
            # Replace NaN with None
            df = df.replace({np.nan: None})
            df = df.assign(CreatedBy=current_user.Email, 
                            FollowUp=False)
            df = df.drop(columns=['CompanyName'])
            
            # Grab max id
            id = Leads.query.order_by(Leads.LeadID.desc()).first()
        
            if id is None:
                    id = 10000
            else:
                id = id.LeadID + 10
            
            # Iterate over rows method
            for index, row in df.iterrows():
                dct = row.to_dict()
                dct.update({'LeadID': id})
                id += 10
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
    users = Users.query.filter_by(ClientID=current_user.ClientID).all()
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
        for user in users]
    form.owner.choices = owners
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
                            CompanySpecialties=form.company_specialties.data\
                                if form.company_specialties.data else None, 
                            CompanyIndustry=form.company_industry.data\
                                if form.company_industry.data else None,
                            CompanyType = form.company_type.data\
                                if form.company_type.data else None, 
                            Owner=form.owner.data if form.owner.data else None,
                            Country=form.country.data, 
                            City=form.city.data if form.city.data else None, 
                            Timezone=form.timezone.data if form.timezone.data else None,
                            ClientID=current_user.ClientID,
                            CreatedBy=current_user.Email)
            
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
    company = request.args.get('account')
    
    users = Users.query.filter_by(ClientID=current_user.ClientID)
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
    for user in users]
    form.owner.choices = owners

    if company:
        form.company.data = company
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
                id = id.LeadID + 10
                
            if account:
                lead = Leads(LeadID=id,
                            AccountID=account.AccountID,
                            ClientID=current_user.ClientID,
                            Position=form.position.data,
                            FirstName=form.first_name.data,
                            LastName=form.last_name.data,
                            Email=form.email.data if form.email.data else None,
                            Owner=form.owner.data if form.owner.data else None,
                            # Status=form.status.data,
                            FollowUp=False,
                            CreatedBy=current_user.Email)
                
                db.session.add(lead)
                db.session.commit()
                flash('Lead added successfully.', 'success')
                return redirect(url_for('leads_list'))
            
        else:
            flash('Account not found.', 'danger')
            return redirect(url_for('new_lead'))
    return render_template('leads/new_lead.html', form=form)

# New opportunity
@app.route('/opportunities/new/', methods=['GET', 'POST'])
@login_required
def new_opportunity():
    account = None
    lead = None
    
    account = request.args.get('account')
    account = Accounts.query.filter_by(ClientID=current_user.ClientID).filter_by(AccountID=account).first()
    if account is None:
        flash('Account not found.', 'danger')
        return redirect(url_for('opportunities_list'))
    
    lead = request.args.get('lead')
    lead = Leads.query.filter_by(ClientID=current_user.ClientID).filter_by(LeadID=lead).first()
    form = OpportunityForm(lead=lead.LeadID, owner=lead.Owner) 
    
    leads = Leads.query.filter_by(AccountID=account.AccountID).all()
    leads = [(0, '-')] + [(lead.LeadID, f'{lead.FirstName} {lead.LastName}') for lead in leads]
    form.lead.choices = leads
    
    users = Users.query.filter_by(ClientID=current_user.ClientID).all()
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
        for user in users]
    form.owner.choices = owners
    
                
    if form.validate_on_submit():
        # Grab max id
        id = None
        id = Opportunities.query.filter_by(ClientID=current_user.ClientID)\
            .order_by(Opportunities.OpportunityID.desc()).first()

        if id is None:
                id = 1000
        else:
            id = id.OpportunityID + 10
        
        date_closed = None if form.stage.data != 'Won' and form.stage.data != 'Loss' \
            else datetime.datetime.now(datetime.timezone.utc)

        try:
            opportunity = Opportunities(OpportunityID=id,
                                        AccountID=account.AccountID,
                                        LeadID=form.lead.data,
                                        ClientID=current_user.ClientID,
                                        Opportunity=form.opportunity.data,
                                        Value=form.value.data,
                                        Stage=form.stage.data,
                                        Owner=lead.Owner if lead else None,
                                        CreatedBy=current_user.Email,
                                        DateClosed=date_closed)
            db.session.add(opportunity)
            db.session.commit()

            flash('Opportunity added successfully.', 'success')
            return redirect(url_for('opportunities_list'))
        except:
            db.session.rollback()
            flash('Opportunity add failed.', 'danger')
            return redirect(url_for('new_opportunity'))
    
    return render_template('opportunities/new_opportunity.html', form=form, account=account)

# New sale
@app.route('/sales/new/', methods=['GET', 'POST'])
@login_required
def new_sale():
    opportunity = None
    opportunity = request.args.get('opportunity')
    if opportunity:
        opportunity = Opportunities.query.filter_by(ClientID=current_user.ClientID)\
            .filter_by(OpportunityID=opportunity).first()
        if opportunity is None:
            flash('Opportunity not found.', 'danger')
            return redirect(url_for('new_sale'))
        
    form = SaleForm(owner=opportunity.Owner)
    form.opportunity.data = opportunity.OpportunityID
    users = Users.query.filter_by(ClientID=current_user.ClientID).all()
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
        for user in users]
    form.owner.choices = owners
    
    if form.validate_on_submit():
        # Grab max id
        id = Sales.query.order_by(Sales.SaleID.desc()).first()
        
        if id is None:
            id = 10000
        else:
            id = id.SaleID + 10
            
        date_closed = None if form.stage.data != 'Won' and form.stage.data != 'Loss' \
            else datetime.datetime.now(datetime.timezone.utc)
      
        try:
            sale = Sales(SaleID=id,
                         AccountID=opportunity.Account.AccountID,
                         LeadID=opportunity.Lead.LeadID,
                         OpportunityID=opportunity.OpportunityID,
                         ClientID=current_user.ClientID,
                         Stage=form.stage.data,
                         Value=form.value.data,
                         Owner=form.owner.data if form.owner.data else None,
                         CreatedBy=current_user.Email,
                         DateClosed=date_closed)
            if opportunity.Stage != 'Won':
                opportunity.Stage = 'Won'
            opportunity.DateClosed = datetime.datetime.now(datetime.timezone.utc)
            
            db.session.add(sale)
            db.session.commit()
            
            flash('Sale added successfully.', 'success')
            return redirect(url_for('sales_list'))
        
        except:
            db.session.rollback()
            flash('Sale add failed.', 'danger')
            return redirect(url_for('new_sale'))
    
    return render_template('sales/new_sale.html', form=form)

# New interaction
@app.route('/interactions/new/', methods=['GET', 'POST'])
@login_required
def new_interaction():
    form = InteractionForm()
    opportunity = None
    opportunity = request.args.get('opportunity')
    if opportunity:
        opportunity = Opportunities.query.filter_by(ClientID=current_user.ClientID)\
        .filter_by(OpportunityID=opportunity).first()
        if opportunity is None:
            flash('Opportunity not found.', 'danger')
            return redirect(url_for('opportunities_list'))
    if form.validate_on_submit():
        try:
            interaction = Interactions(Interaction=form.interaction.data,
                                        OpportunityID=opportunity.OpportunityID,
                                        ClientID=current_user.ClientID,
                                        CreatedBy=current_user.Email)
            db.session.add(interaction)
            db.session.commit()
            flash('Interaction added successfully.', 'success')
        except:
            flash('Interaction add failed.', 'danger')
        return redirect(url_for('opportunity', id=opportunity.OpportunityID))

    
    return render_template('new_interaction.html',  form=form, opportunity=opportunity)

# Update account
@app.route('/accounts/update/<int:id>/', methods=['GET', 'POST'])
@login_required
def account(id):
    account = None
    account = Accounts.query.filter_by(ClientID=current_user.ClientID).filter_by(AccountID=id).first()
    if account is None:
        flash('Account not found.', 'danger')
        return redirect(url_for('accounts_list'))
    
    form = AccountForm(owner=account.Owner)
    form.company_specialties.data = account.CompanySpecialties
    users = Users.query.filter_by(ClientID=current_user.ClientID).all()
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
        for user in users]
    form.owner.choices = owners
    
    if form.validate_on_submit():
        try:
            account.CompanyName = form.company_name.data
            account.CompanyRevenue = form.company_revenue.data
            account.EmployeeHeadCount = form.employee_head_count.data
            account.CompanySpecialties = request.form.get('company_specialties')\
                if request.form.get('company_specialties') else None
            account.CompanyType = form.company_type.data \
                if form.company_type.data else None
            account.Owner = form.owner.data if form.owner.data else None
            account.Country = form.country.data
            account.City = form.city.data if form.city.data else None
            account.Timezone = form.timezone.data if form.timezone.data else None
            
            db.session.commit()
            flash('Account updated successfully.', 'success')
            
        except:
            flash('Account update failed.', 'danger')
        
        return redirect(url_for('account', id=id))

        
    return render_template('accounts/account.html', form=form, account=account,
            id=id)   

# Update lead
@app.route('/leads/update/<int:id>/', methods=['GET', 'POST'])
@login_required
def lead(id):
    lead = None
    lead = Leads.query.filter_by(ClientID=current_user.ClientID).filter_by(LeadID=id).first()    
    if lead is None:
        flash('Lead not found.', 'danger')
        return redirect(url_for('leads_list'))
    form = LeadUpdateForm(status=lead.Status, owner=lead.Owner)
    users = Users.query.filter_by(ClientID=current_user.ClientID).all()
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
        for user in users]
    form.owner.choices = owners
    
    if form.validate_on_submit():
        try:
            lead.Position = form.position.data
            lead.FirstName = form.first_name.data
            lead.LastName = form.last_name.data
            lead.Email = form.email.data if form.email.data else None
            lead.Owner = form.owner.data if form.owner.data else None
            db.session.commit()
            flash('Lead updated successfully.', 'success')
        
        except:
            flash('Lead update failed.', 'danger')
        
        return redirect(url_for('lead', id=id))
    
    return render_template('leads/lead.html', lead=lead, form=form)

# Update lead follow up
@app.route('/leads/follow_up/<int:id>/', methods=['GET', 'POST'])
@login_required
def follow_up(id):
    lead = None
    lead = Leads.query.filter_by(ClientID=current_user.ClientID).filter_by(LeadID=id).first()
    if lead is None:
        flash('Lead not found.', 'danger')
        return redirect(url_for('leads_list')) 
    view = request.args.get('view')
    
    try:
        lead.FollowUp = False if lead.FollowUp else True
        db.session.commit()
    except:
        flash('Follow-up status update failed.', 'danger')
        if view:
            return redirect(url_for('lead', id=id))
        return redirect(url_for('leads_list'))
    
    if view:
        flash('Follow-up status updated.', 'success')
        return redirect(url_for('lead', id=id))
    flash(f'Follow-up status for {lead.FirstName} {lead.LastName} updated.', 'success')
    return redirect(url_for('leads_list'))

# Update opportunity
@app.route('/opportunities/update/<int:id>/', methods=['GET', 'POST'])
@login_required
def opportunity(id):
    opportunity = None
    opportunity = Opportunities.query.filter_by(ClientID=current_user.ClientID).filter_by(OpportunityID=id).first()
    if opportunity:
        leads = Leads.query.filter_by(AccountID=opportunity.Account.AccountID).all()
        leads = [(lead.LeadID, f'{lead.FirstName} {lead.LastName}') for lead in leads]
        form = OpportunityUpdateForm(lead=opportunity.LeadID, 
                                     stage=opportunity.Stage,
                                     owner=opportunity.Owner)
        form.lead.choices = leads
        form.opportunity.data = opportunity.Opportunity
        users = Users.query.filter_by(ClientID=current_user.ClientID).all()
        owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
            for user in users]
        form.owner.choices = owners
    else:
        flash('Opportunity not found.', 'danger')
        return redirect(url_for('opportunities_list'))
    
    if form.validate_on_submit():
        try:
            opportunity.LeadID = form.lead.data
            opportunity.Opportunity = request.form.get('opportunity')
            opportunity.Value = form.value.data
            opportunity.Stage = form.stage.data
            opportunity.Owner = form.owner.data if form.owner.data else None
            if form.stage.data == 'Won' or form.stage.data == 'Loss':
                opportunity.DateClosed = datetime.datetime.now(datetime.timezone.utc)
            else:
                opportunity.DateClosed = None
            db.session.commit()
            flash('Opportunity updated successfully.', 'success')

        except:
            flash('Opportunity update failed.', 'danger')
            
        return redirect(url_for('opportunity', id=id))
        
    return render_template('opportunities/opportunity.html', form=form, opportunity=opportunity)

# Update sale
@app.route('/sales/update/<int:id>/', methods=['GET', 'POST'])
@login_required
def sale(id):
    sale = None
    sale = Sales.query.filter_by(ClientID=current_user.ClientID)\
        .filter_by(SaleID=id).first()
    if sale is None:
        flash('Sale not found.', 'danger')
        return redirect(url_for('sales_list'))
    form = SaleUpdateForm(stage=sale.Stage)
    users = Users.query.filter_by(ClientID=current_user.ClientID).all()
    owners = [(0, 'Not assigned')] + [(user.UserID, f'{user.FirstName} {user.LastName}')\
        for user in users]
    form.owner.choices = owners

    if form.validate_on_submit():
        try:
            sale.Stage = form.stage.data
            sale.Value = form.value.data
            sale.Owner = form.owner.data if form.owner.data else None
            if form.stage.data == 'Won' or form.stage.data == 'Loss':
                sale.DateClosed = datetime.datetime.now(datetime.timezone.utc)
            else:
                sale.DateClosed = None
            db.session.commit()
            flash('Sale updated successfully.', 'success')
            
        except:
            flash('Sale update failed.', 'danger')
            
        return redirect(url_for('sale', id=id))
    return render_template('sales/sale.html', form=form, sale=sale)

# Update interaction
@app.route('/interactions/view/<int:id>/', methods=['GET', 'POST'])
@login_required
def interaction(id):
    interaction = None
    interaction = Interactions.query.filter_by(ClientID=current_user.ClientID)\
        .filter_by(InteractionID=id).first()
    if interaction is None:
        flash('Interaction not found.', 'danger')
        return redirect(url_for('opportunities_list'))
    form = InteractionForm()
    form.interaction.data = interaction.Interaction

    if form.validate_on_submit():
        try:
            interaction.Interaction = request.form.get('interaction')
            db.session.commit()
            flash('Interaction updated succesfully.', 'success')
            
        except:
            flash('Interaction update failed', 'danger')
            
        return redirect(url_for('interaction', id=id))
    
    return render_template('interaction.html', form=form, interaction=interaction)

# Delete account
@app.route('/accounts/delete/<int:id>/')
@login_required
def delete_account(id):
    account = None
    account = Accounts.query.filter_by(ClientID=current_user.ClientID).filter_by(AccountID=id).first()
    if account is None:
        flash('Account not found.', 'danger')
        return redirect(url_for('accounts_list'))
    
    if account.Leads:
        flash('Account cannot be deleted as it has associated leads.', 'danger')
        return redirect(url_for('account', id=account.AccountID))
    try:
        db.session.delete(account)
        db.session.commit()
        flash('Account deleted successfully.', 'success')
    except:
        flash('Error deleting account.', 'danger') 
    return redirect(url_for('accounts_list'))
    
# Delete lead
@app.route('/leads/delete/<int:id>/')
@login_required
def delete_lead(id):
    lead = None
    lead = Leads.query.filter_by(ClientID=current_user.ClientID).filter_by(LeadID=id).first()
    if lead is None:
        flash('Lead not found.', 'danger')
        return redirect(url_for('leads_list'))
    
    if lead.Opportunities:
        flash('Lead cannot be deleted as it has associated opportunities.', 'danger')
        return redirect(url_for('lead', id=lead.LeadID))
    try:
        db.session.delete(lead)
        db.session.commit()
        flash('Lead deleted successfully.', 'success')
    except:
        flash('Error deleting lead.', 'danger')
    return redirect(url_for('leads_list'))

# Delete opportunity
@app.route('/opportunities/delete/<int:id>/')
@login_required
def delete_opportunity(id):
    opportunity = None
    opportunity = Opportunities.query.filter_by(ClientID=current_user.ClientID).filter_by(OpportunityID=id).first()
    if opportunity is None:
        flash('Opportunity not found.', 'danger')
        return redirect(url_for('opportunities_list'))
    if opportunity.Sales:
        flash('Opportunity cannot be deleted as it has associated sales.', 'danger')
        return redirect(url_for('opportunity', id=opportunity.OpportunityID))
    try:
        db.session.delete(opportunity)
        db.session.commit()
        flash('Opportunity deleted successfully.', 'success')
    except:
        flash('Error deleting opportunity.', 'danger')
        
    return redirect(url_for('opportunities_list'))
    
# Delete sale
@app.route('/sales/delete/<int:id>/')
@login_required
def delete_sale(id):
    sale = None
    sale = Sales.query.filter_by(ClientID=current_user.ClientID).filter_by(SaleID=id).first()
    if sale is None:
        flash('Sale not found.', 'danger')
        return redirect(url_for('sales_list'))
    try:
        db.session.delete(sale)
        db.session.commit()
        flash('Sale deleted successfully.', 'success')
    except:
        flash('Error deleting sale.', 'danger')
    return redirect(url_for('sales_list'))

# Delete interaction
@app.route('/interactions/delete/<int:id>/')
@login_required
def delete_interaction(id):
    interaction = None
    interaction = Interactions.query.filter_by(ClientID=current_user.ClientID)\
        .filter_by(InteractionID=id).first()
    if interaction is None:
        flash('Interaction not found.', 'danger')
        return redirect(url_for('opportunities_list'))
    opportunity = interaction.Opportunity.OpportunityID
    try:
        db.session.delete(interaction)
        db.session.commit()
        flash('Interaction deleted successfully.', 'success')
    except:
        flash('Error deleting interaction.', 'danger')
    return redirect(url_for('opportunity', id=opportunity))

# Clear accounts
@app.route('/accounts/clear/')
@login_required
def clear_accounts():
    try:
        Accounts.query.delete()
        db.session.commit()
        flash('Accounts cleared successfully.', 'success')
    except:
        flash('Accounts clear failed. Foreign key relationships may exist.', 'danger')
    return redirect(url_for('accounts_list'))

# Clear leads
@app.route('/leads/clear/')
@login_required
def clear_leads():
    try:
        Leads.query.delete()
        db.session.commit()
        flash('Leads cleared successfully.', 'success')
    except:
        flash('Leads clear failed. Foreign key relationships may exist.', 'danger')
    return redirect(url_for('leads_list'))

# Clear opportunities
@app.route('/opportunities/clear/')
@login_required
def clear_opportunities():  
    try:
        Opportunities.query.delete()
        db.session.commit()
        flash('Opportunities cleared successfully.', 'success')
    except:
        flash('Opportunities clear failed. Foreign key relationships may exist.', 'danger')

    return redirect(url_for('opportunities_list'))

# Clear sales
@app.route('/sales/clear/')
@login_required
def clear_sales():
    try:
        Sales.query.delete()
        db.session.commit()
        flash('Sales cleared successfully.', 'success')
    except:
        flash('Sales clear failed. Foreign key relationships may exist.', 'danger')

    return redirect(url_for('sales_list'))

# Clear interactions
@app.route('/interactions/clear/')
@login_required
def clear_interactions():
    try:
        Interactions.query.delete()
        db.session.commit()
        flash('Interactions cleared successfully.', 'success')
    except:
        flash('Interactions clear failed.', 'danger')

    return redirect(url_for('opportunities_list'))

# Search accounts
@app.route('/search_accounts/')
@login_required
def search_accounts():
    query = request.args.get('query')
    if query:
        accounts = Accounts.query.filter_by(ClientID=current_user.ClientID)\
            .filter(Accounts.CompanyName.icontains(query) |\
            Accounts.Country.icontains(query) | 
            Accounts.City.icontains(query) |
            Accounts.CompanyType.icontains(query) |
            Accounts.Owner.icontains(query) |
            Accounts.CompanyIndustry.icontains(query) |
            Accounts.Timezone.icontains(query))
    else:
        accounts = Accounts.query.filter_by(ClientID=current_user.ClientID)\
            .order_by(Accounts.AccountID.desc()).limit(100)
    return render_template('accounts/search_accounts.html', accounts=accounts)

# Search leads
@app.route('/search_leads/')
@login_required
def search_leads():
    query = request.args.get('query')
    if query:
        leads = Leads.query.filter_by(ClientID=current_user.ClientID)\
            .join(Accounts, Leads.AccountID == Accounts.AccountID)\
            .filter((Leads.FirstName + ' ' + Leads.LastName).icontains(query) |
            Leads.FirstName.icontains(query) |
            Leads.LastName.icontains(query) |
            Leads.Position.icontains(query) |
            Leads.Email.icontains(query) |
            Leads.Status.icontains(query) |
            Leads.Owner.icontains(query) |
            Accounts.CompanyName.icontains(query) |
            Accounts.City.icontains(query))
    else:
        leads = Leads.query.filter_by(ClientID=current_user.ClientID)\
            .order_by(Leads.LeadID.desc()).limit(100)
    return render_template('leads/search_leads.html', leads=leads)

# Search opportunities
@app.route('/search_opportunities/')
@login_required
def search_opportunities():
    query = request.args.get('query')
    if query:
        opportunities = Opportunities.query.filter_by(ClientID=current_user.ClientID)\
            .join(Accounts, Opportunities.AccountID == Accounts.AccountID)\
            .join(Leads, Opportunities.LeadID == Leads.LeadID)\
            .filter(Opportunities.Opportunity.icontains(query) |
            (Leads.FirstName + ' ' + Leads.LastName).icontains(query) |
            Opportunities.Value.icontains(query) |
            Opportunities.Stage.icontains(query) |
            Opportunities.Owner.icontains(query) |
            Leads.FirstName.icontains(query) |
            Leads.LastName.icontains(query) |
            Accounts.CompanyName.icontains(query))
    else:
        opportunities = Opportunities.query.filter_by(ClientID=current_user.ClientID)\
            .order_by(Opportunities.OpportunityID.desc()).limit(100)
    return render_template('opportunities/search_opportunities.html', opportunities=opportunities)

# Search sales
@app.route('/search_sales/')
@login_required
def search_sales():
    query = request.args.get('query')
    if query:
        sales = Sales.query.filter_by(ClientID=current_user.ClientID)\
            .join(Accounts, Sales.AccountID == Accounts.AccountID)\
            .join(Leads, Sales.LeadID == Leads.LeadID)\
            .filter((Leads.FirstName + ' ' + Leads.LastName).icontains(query) |
            Sales.Value.icontains(query) |
            Sales.Stage.icontains(query) |
            Sales.Owner.icontains(query) |
            Leads.FirstName.icontains(query) |
            Leads.LastName.icontains(query) |
            Accounts.CompanyName.icontains(query))
    else:
        sales = Sales.query.filter_by(ClientID=current_user.ClientID)\
            .order_by(Sales.SaleID.desc()).limit(100)
    return render_template('sales/search_sales.html', sales=sales)

    
# Invalid URL
@app.errorhandler(404)
def page_not_foredid(e):
    return redirect(url_for('index'))

# Internal server error
@app.errorhandler(500)
def internal_server_error(e):
    return e

##############################################################################

# Models

# Clients model
class Clients(db.Model):
    __tablename__ = 'Clients'
    ClientID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Client = db.Column(db.String(50), nullable=False, unique=True)
    License = db.Column(db.String(20), nullable=False, unique=True)
    # Image = db.Column(db.String(255), unique=True)
    ValidFrom = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    ValidTo = db.Column(db.Date)
    
    # References
    Users = db.relationship('Users', backref='Client')
    Accounts = db.relationship('Accounts', backref='Client')
    Leads = db.relationship('Leads', backref='Clients')
    Opportunities = db.relationship('Opportunities', backref='Client')
    Sales = db.relationship('Sales', backref='Client')
    Interactions = db.relationship('Interactions', backref='Client')
    
# Users model
class Users(db.Model, UserMixin):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    Email = db.Column(db.String(50), unique=True, nullable=False)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)
    License = db.Column(db.String(20), nullable=False)
    ValidFrom = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    ValidTo = db.Column(db.Date)
    
    # References
    Accounts = db.relationship('Accounts', backref='User')
    Leads = db.relationship('Leads', backref='User')
    Opportunities = db.relationship('Opportunities', backref='User')
    Sales = db.relationship('Sales', backref='User')
    Interactions = db.relationship('Interactions', backref='User')

    
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
        return True  # Assuming the presence of a valid session token
    
# Accounts model
class Accounts(db.Model):
    __tablename__ = 'Accounts'
    AccountID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    CompanyName = db.Column(db.String(100), nullable=False)
    CompanyRevenue = db.Column(db.Integer, nullable=False)
    EmployeeHeadCount = db.Column(db.Integer, nullable=False)
    CompanyIndustry = db.Column(db.String(100))
    CompanySpecialties = db.Column(db.Text)
    CompanyType = db.Column(db.String(50))
    Country = db.Column(db.String(50), nullable=False)
    City = db.Column(db.String(50))
    Timezone = db.Column(db.String(50))
    Owner = db.Column(db.String(50), db.ForeignKey(Users.UserID)) # Foreign key to UserID
    CreatedBy = db.Column(db.String(50))
    DateCreated = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    
    # References
    Leads = db.relationship('Leads', backref='Account')
    Opportunities = db.relationship('Opportunities', backref='Account')
    Sales = db.relationship('Sales', backref='Account')
    
# Leads model
class Leads(db.Model):
    __tablename__ = 'Leads'
    LeadID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AccountID = db.Column(db.Integer, db.ForeignKey(Accounts.AccountID)) # Foreign key to AccountID
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    Position = db.Column(db.String(75), nullable=False)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(50))
    # CompanyName =  db.Column(db.String(100), nullable=False)
    Owner = db.Column(db.String(50), db.ForeignKey(Users.UserID)) # Foreign key to UserID
    Status = db.Column(db.String(50))
    FollowUp = db.Column(db.Boolean)
    CreatedBy = db.Column(db.String(50)) 
    DateCreated = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    
    # References
    Opportunities = db.relationship('Opportunities', backref='Lead')
    Sales = db.relationship('Sales', backref='Lead')


# Opportunities model    
class Opportunities(db.Model):
    __tablename__ = 'Opportunities'
    OpportunityID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AccountID = db.Column(db.Integer, db.ForeignKey(Accounts.AccountID)) # Foreign Key to AccountID
    LeadID = db.Column(db.Integer, db.ForeignKey(Leads.LeadID)) # Foreign key to LeadID
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    Opportunity = db.Column(db.Text)
    Value = db.Column(db.Integer)
    Stage = db.Column(db.String(100))
    Owner = db.Column(db.String(50), db.ForeignKey(Users.UserID))
    CreatedBy = db.Column(db.String(50))
    DateCreated = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    DateClosed = db.Column(db.Date)

    # References
    Sales = db.relationship('Sales', backref='Opportunity')
    Interactions = db.relationship('Interactions', backref='Opportunity')

# Sales model
class Sales(db.Model):
    __tablename__ = 'Sales'
    SaleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OpportunityID = db.Column(db.Integer, db.ForeignKey(Opportunities.OpportunityID)) # Foreign key to OpportunityID
    AccountID = db.Column(db.Integer, db.ForeignKey(Accounts.AccountID)) # Foreign Key to AccountID
    LeadID = db.Column(db.Integer, db.ForeignKey(Leads.LeadID)) # Foreign key to LeadID
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    Value = db.Column(db.Integer)
    Stage = db.Column(db.String(50))
    Owner = db.Column(db.String(50), db.ForeignKey(Users.UserID))
    CreatedBy = db.Column(db.String(50))
    DateCreated = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))
    DateClosed = db.Column(db.Date)
    
# Interactions model
class Interactions(db.Model):
    __tablename__ = 'Interactions'
    InteractionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OpportunityID = db.Column(db.Integer, db.ForeignKey(Opportunities.OpportunityID)) # Foreign key to OpportunityID
    ClientID = db.Column(db.Integer, db.ForeignKey(Clients.ClientID)) # Foreign key to ClientID
    Interaction = db.Column(db.Text)
    CreatedBy = db.Column(db.String(50), db.ForeignKey(Users.Email)) # Foreign key to Email
    DateCreated = db.Column(db.Date, default=datetime.datetime.now(datetime.timezone.utc))    
    
# Admins model
class Admins(db.Model):
    __tablename__ = 'Admins'
    User = db.Column(db.String(50), primary_key=True)
    
# Alembic model
class Alembic(db.Model):
    __tablename__ = 'alembic_version'
    version_num = db.Column(db.String(32), primary_key=True)

##############################################################################
if __name__ == "__main__":
    app.run(debug=True)
