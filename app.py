from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine


from sqlalchemy import create_engine
app = Flask(__name__)

db_addr = "postgres://"+"postgres"+":"+"whatevergoes"+"@"+"database-1.ci1szttxojrb.us-east-1.rds.amazonaws.com"+":"+"5432"+"/"+"stockapp"

eng = create_engine(db_addr)


# Index Page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_tables')
def create_tables():
    with eng.connect() as con:

        create_transactions = """ 
        CREATE TABLE Transactions (
        id SERIAL,
        buyPrice FLOAT NOT NULL,
        quantity INT NOT NULL,
        date TIMESTAMP NOT NULL,
        userId INT REFERENCES Users(id),
        ticker CHAR REFERENCES Stocks(ticker),
        PRIMARY KEY (id)
        );"""

        create_stocks= """ 
        CREATE TABLE Stocks (
        ticker CHAR NOT NULL,
        closePrice FLOAT NOT NULL,
        openPrice FLOAT NOT NULL,
        latestDate TIMESTAMP NOT NULL,
        PRIMARY KEY (ticker)
        );"""

        create_watchList = """ 
        CREATE TABLE WatchList (
        id SERIAL,
        userID INT REFERENCES Users(id),
        PRIMARY KEY (id)
        );"""

        #Table for many-to-many relationship between watchlist and stocks
        create_watchlist_to_stock = """ 
        CREATE TABLE watchlistToStock (
        watchListId INT REFERENCES WatchList(id),
        ticker INT REFERENCES Stocks(ticker),

        PRIMARY KEY (watchListId, 'ticker')
        UNIQUE(watchListId, ticker)
        );"""

        create_users = """ 
        CREATE TABLE Users (
        id SERIAL,
        name CHAR NOT NULL,
        email CHAR NOT NULL,
        username CHAR NOT NULL,
        password CHAR NOT NULL,
        loginTime TIMESTAMP NOT NULL,
        regTime TIMESTAMP NOT NULL,
        PRIMARY KEY (id)
        );"""

        rs_u = con.execute(create_users)
        print ("Created Users Table") 

        rs_w = con.execute(create_watchList)
        print ("Created Watchlist Table") 

        rs_s = con.execute(create_stocks)
        print ("Created Stocks Table") 

        rs_t = con.execute(create_transactions)
        print ("Created Tranasction Table") 
    return "Finished Creating Tables"

       


if __name__ == '__main__':
    app.run(debug=True)