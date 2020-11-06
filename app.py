from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField, DateField, DecimalField
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sys

from sqlalchemy import create_engine
app = Flask(__name__)
app.secret_key = "super secret key"

db_addr = "postgres://"+"postgres"+":"+"whatevergoes"+"@" + \
    "database-1.ci1szttxojrb.us-east-1.rds.amazonaws.com"+":"+"5432"+"/"+"stockapp"

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
        ticker VARCHAR(225) REFERENCES Stocks(ticker),
        PRIMARY KEY (id)
        );"""

        create_stocks = """ 
        CREATE TABLE Stocks (
        ticker VARCHAR(225) NOT NULL,
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

        # Table for many-to-many relationship between watchlist and stocks
        create_watchlist_to_stock = """ 
        CREATE TABLE watchlistToStock (
        watchListId INT REFERENCES WatchList(id),
        ticker VARCHAR(225) REFERENCES Stocks(ticker),

        PRIMARY KEY (watchListId, ticker)
        );"""

        create_users = """ 
        CREATE TABLE Users (
        id SERIAL,
        name VARCHAR(225) NOT NULL,
        email VARCHAR(225) NOT NULL,
        username VARCHAR(225) NOT NULL,
        password VARCHAR(225) NOT NULL,
        loginTime TIMESTAMP NOT NULL,
        regTime TIMESTAMP NOT NULL,
        PRIMARY KEY (id)
        );"""

        rs_u = con.execute(create_users)
        print("Created Users Table")

        rs_w = con.execute(create_watchList)
        print("Created Watchlist Table")

        rs_s = con.execute(create_stocks)
        print("Created Stocks Table")

        rs_t = con.execute(create_transactions)
        print("Created Tranasction Table")

        rs_ws = con.execute(create_watchlist_to_stock)
        print("Created WatchList and Stock Relation Table")

    return "Finished Creating Tables"

# Check if user logged in


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Registration Form


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=4, max=30)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# Route for User Registration Page


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name_input = form.name.data
        email_input = form.email.data
        username_input = form.username.data
        password_input = form.password.data
        loginTime_input = datetime.now()
        regTime_input = datetime.now()

        data = {
            "name": name_input,
            "email": email_input,
            "username": username_input,
            "password": password_input,
            "loginTime": loginTime_input,
            "regTime": regTime_input
        }

        with eng.connect() as con:
            add_user = text("""
            INSERT INTO Users (name, email, username, password, loginTime, regTime)
            VALUES (:name, :email, :username, :password, :loginTime, :regTime);
            """)

            exe = con.execute(add_user, **data)

        with eng.connect() as con:
            find_user = """
            SELECT *
            FROM Users
            WHERE username = '""" + str(username_input) + """';
            """

            user = con.execute(find_user)
            user = user.first()

        data = {
            "userId": user[0]
        }
        with eng.connect() as con:
            add_watchlist = text(
                "INSERT INTO WatchList (userID) VALUES (:userId);")

            exe = con.execute(add_watchlist, **data)

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# Route for login page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usernameLogin = request.form['username']
        password_candidate = request.form['password']

        user = 0

        with eng.connect() as con:
            find_user = """
            SELECT *
            FROM Users
            WHERE username = '""" + str(usernameLogin) + """';
            """

            user = con.execute(find_user)
            user = user.first()

        with eng.connect() as con:
            find_watchlist = """
                SELECT *
                FROM WatchList
                WHERE userID = """ + str(user[0]) + """;
            """
            watchlist = con.execute(find_watchlist)
            watchlist = watchlist.first()

        if user[3] is None or user[3] == "":
            error = 'Username Not Found'
            return render_template('login.html', error=error)
        else:
            if password_candidate == user[4]:
                session['logged_in'] = True
                session['username'] = user[3]
                session['userid'] = user[0]
                session['watchlistid'] = watchlist[0]

                # now = datetime.now()

                # with eng.connect() as con:
                #     con.execute(
                #         "UPDATE Users SET loginTime = "+str(now)[:19]+"WHERE id = "+str(user[0])+";")

                flash('You are logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', error=error)

    return render_template('login.html')

# Route for dashboard


@app.route('/dashboard')
@is_logged_in
def dashboard():

    # with eng.connect as con:
    #     watchlistitem = """
    #         SELECT *
    #         FROM WatchList
    #         WHERE id = """+session['user_id']+""";
    #     """

    #     userwatchlist = con.execute(watchlistitem)

    # userwatchlist = WatchList.query.filter_by(user_id = session['userid']).all()
    # stocks = []
    # # details = []

    # for item in userwatchlist:
    #     with eng.connect as con:
    #         comp = """
    #             SELECT *
    #             FROM Stocks
    #             WHERE id = item['stockID']
    #         """

    #         addstock = con.execute(comp)
    #     # addstock = StockInfo.query.filter_by(id=item.stockinfo_id).first()
    #         stocks.append(addstock)

    # # for item in stocks:
    # #     addDetails = StockPriceDetails.query.filter_by(
    # #         stock_id=item.id).first()
    # #     details.append(addDetails)

    # if len(stocks) == 0:
    #     error = 'You are not tracking any stocks'
    #     return render_template('dashboard.html', error=error, stocks=stocks)
    # else:
    #     return render_template('dashboard.html', stocks=stocks)
    return render_template('dashboard.html')  # , stocks=stocks)

# Search Form


class SearchForm(Form):
    ticker = StringField('Ticker', [validators.DataRequired()])

# Route for Price page for top 10 price change in the market


@app.route('/prices', methods=['GET', 'POST'])
@is_logged_in
def prices():
    form = SearchForm(request.form)
    if request.method == 'POST' and form.validate():
        ticker_input = form.ticker.data

        with eng.connect() as con:
            searchticker = """
                SELECT *
                FROM Stocks
                WHERE ticker = '""" + str(ticker_input) + """';
            """

            prices = con.execute(searchticker)
            prices = prices.fetchall()

        if len(prices) == 0:
            error = 'No such company found. Try again'
            with eng.connect() as con:
                searchticker = """
                    SELECT *
                    FROM Stocks;
                """

                prices = con.execute(searchticker)
                prices = prices.fetchall()
            return render_template('prices.html', prices=prices, form=form, error=error)
        else:
            flash('Here are your search results', 'success')
            return render_template('prices.html', prices=prices, form=form)
    with eng.connect() as con:
        searchticker = """
                SELECT *
                FROM Stocks;
            """

        prices = con.execute(searchticker)
        prices = prices.fetchall()
    return render_template('prices.html', prices=prices, form=form)

@app.route('/transactions', methods=['GET', 'POST'])
@is_logged_in
def transactions():
    form = SearchForm(request.form)
    if request.method == 'POST' and form.validate():
        ticker_input = form.ticker.data

        with eng.connect() as con:
            searchtransactions= """
                SELECT *
                FROM Transactions
                WHERE ticker = '""" + str(ticker_input) + """' AND userId = """ + str(session['userid']) + """;
            """

            ts = con.execute(searchtransactions)
            ts = ts.fetchall()

        if len(ts) == 0:
            error = 'No such transactions found. Try again'
            with eng.connect() as con:
                searchtransactions= """
                SELECT *
                FROM Transactions
                WHERE userId = """ + str(session['userid']) + """;
                """

                ts = con.execute(searchtransactions)
                ts = ts.fetchall()

            return render_template('transactions.html', transactions=ts, form=form, error=error)
        else:
            flash('Here are your search results', 'success')
            return render_template('transactions.html', transactions=ts, form=form)
    with eng.connect() as con:
        searchtransactions= """
            SELECT *
            FROM Transactions
            WHERE userId = """ + str(session['userid']) + """;
        """

        ts = con.execute(searchtransactions)
        ts = ts.fetchall()
    return render_template('transactions.html', transactions=ts, form=form)


class TransactionForm(Form):
    buyPrice = DecimalField('Buy_Price', [validators.DataRequired()])
    quantity = IntegerField('Quantity', [validators.DataRequired()])
    # date = DateField('Date', [validators.DataRequired()])
    ticker = StringField('Ticker', [validators.DataRequired()])


@app.route('/add_transaction', methods=['GET', 'POST'])
@is_logged_in
def add_transaction():
    form = TransactionForm(request.form)
    if request.method == 'POST' and form.validate():
        buyPrice = form.buyPrice.data
        quantity = form.quantity.data
        # date = form.date.data
        ticker = form.ticker.data

        data = {
            "buyPrice": buyPrice,
            "quantity": quantity,
            "date": datetime.now(),
            "ticker": ticker,
            "userId" : session['userid']
        }

        with eng.connect() as con:
            search_ticker= """
                SELECT *
                FROM Stocks
                WHERE ticker = '""" + str(ticker) +"""';
            """

            s = con.execute(search_ticker)
            s = s.fetchall()

        if len(s) == 0:
            error = 'No such ticker found in our data base. Try again'

            return render_template('add_transaction.html', form=form, error=error)
        else:
            # print(buyPrice, file=sys.stderr)
            with eng.connect() as con:
                insert_t = text("""
                INSERT INTO Transactions (buyPrice, quantity, date, userId, ticker)
                VALUES (:buyPrice, :quantity, :date, :userId, :ticker);
                """)

                ts = con.execute(insert_t, **data)
                # ts = ts.fetchall()

        
            flash('Your Transaction has been added. Go to the Transaction tab to view it.', 'success')
            return render_template('add_transaction.html', form=form)
    
    return render_template('add_transaction.html', form=form)

@app.route('/delete_transaction/<int:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_transaction(id):
    if request.method:

        with eng.connect() as con:
            search_ticker= """
                DELETE FROM Transactions
                WHERE id = """ + str(id) +""";
            """

            s = con.execute(search_ticker)
        flash('Your Transaction has been deleted.', 'success')

    
    return redirect(url_for('transactions'))

class UpdateForm(Form):
    buyPrice = DecimalField('Buy_Price', [validators.DataRequired()])
    quantity = IntegerField('Quantity', [validators.DataRequired()])
    # date = DateField('Date', [validators.DataRequired()])

@app.route('/update_transaction/<int:id>', methods=['GET', 'POST'])
@is_logged_in
def update_transaction(id):
    form = UpdateForm(request.form)
    if request.method == 'POST' and form.validate():
        buyPrice = form.buyPrice.data
        quantity = form.quantity.data

        data = {
            "buyPrice": buyPrice,
            "quantity": quantity,
        }
        with eng.connect() as con:
            update_t= """
                UPDATE Transactions
                SET buyPrice = """ + str(buyPrice) + """, quantity = """ + str(quantity) + """
                WHERE id = """ + str(id) +""";
            """
            s = con.execute(update_t)

        flash('Your Transaction has been updated.', 'success')
        return redirect(url_for('transactions'))
    
    return render_template('update_transaction.html', form=form)

# @app.route('/update_transaction/<int:id>', methods=['POST'])
# @is_logged_in
# def update_transaction(id):
#     if request.method == 'POST':

#         with eng.connect() as con:
#             search_ticker= """
#                 UPDATE Transactions
#                 SET Stocks
#                 WHERE ticker = '""" + str(ticker) +"""';
#             """

#             s = con.execute(search_ticker)
#             s = s.fetchall()
#             flash('Your Transaction has been updated.', 'success')

    
#     return redirect(url_for('transactions'))

# Route for logout


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
