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

# MySQL database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://erpcrm:Erpcrmpass1!@erpcrmdb.cfg0ok8iismy.us-west-1.rds.amazonaws.com:3306/erpcrmdb' 

# Secret key
app.config['SECRET_KEY'] = '9b2a012a1a1c425a8c86'

# Uploads folder
app.config['UPLOAD_FOLDER'] = 'static/files'

# Set session timeout duration
app.permanent_session_lifetime = timedelta(minutes=30)

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db) 

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
    Lead = db.relationship('Leads', backref='Account')
    Opportunity = db.relationship('Opportunities', backref='Account')
    
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
    Opportunity = db.relationship('Opportunities', backref='Lead')


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

# Routes

@app.route('/')
def index():
    return render_template('index.html')

# Accounts list
@app.route('/accounts/accounts_list/')
def accounts_list():
    accounts = None
    try:
        accounts = Accounts.query.order_by(Accounts.AccountID.desc()).all()
    except:
        flash('Error loading accounts. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('accounts/accounts_list.html', accounts=accounts)

# Accounts import
@app.route('/accounts/accounts_import/', methods=['GET', 'POST'])
def accounts_import():
    return render_template('accounts_import.html')

# New Account
@app.route('/accounts/new_account/', methods=['GET', 'POST'])
def new_account():
    form = AccountForm()
    try:
        if form.validate_on_submit():
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
                            ClientID=100000)
            
            db.session.add(account)
            db.session.commit()
            
            flash('Account added successfully.', 'success')
            return redirect(url_for('accounts_list'))
        
    except:
        flash('Error adding account. Please try again.', 'error')
        return redirect(url_for('new_account'))
           
    return render_template('accounts/new_account.html', form=form)

# Update account
@app.route('/accounts/update_account/<int:id>', methods=['GET', 'POST'])
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
            flash('Account update failed.', 'error')
            return redirect(url_for('account', id=id))

        
    return render_template('accounts/account.html', form=form, account=account, id=id)    

# Delete account
@app.route('/accounts/delete_account/<int:id>')
def delete_account(id):
    account = Accounts.query.get_or_404(id)
    try:
        db.session.delete(account)
        db.session.commit()
        flash('Account deleted successfully.', 'success')
        return redirect(url_for('accounts_list'))
    
    except:
        flash('Error deleting account.', 'error')
        return redirect(url_for('accounts_list'))




if __name__ == "__main__":
    app.run(debug=True)