from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine


from sqlalchemy import create_engine
app = Flask(__name__)

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
        ticker CHAR REFERENCES Stocks(ticker),
        PRIMARY KEY (id)
        );"""

        create_stocks = """ 
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
        stockID INT REFERENCES Stocks(id),
        PRIMARY KEY (id)
        );"""

        # Table for many-to-many relationship between watchlist and stocks
        create_watchlist_to_stock = """ 
        CREATE TABLE watchlistToStock (
        watchListId INT REFERENCES WatchList(id),
        ticker CHAR REFERENCES Stocks(ticker),

        PRIMARY KEY (watchListId, ticker)
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
        password_input = sha256_crypt.encrypt(str(form.password.data))
        loginTime_input = datetime.now()
        regTime_input = datetime.now()

        with eng.begin() as con:
            r1 = con.execute(Users.select())
            con.execute(Users.insert(), {"name": name_input, "email": email_input, "username": username_input, "password": password_input,
                                         "loginTime": loginTime_input, "regTime": regTime_input})

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# Route for login page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usernameLogin = request.form['username']
        password_candidate = request.form['password']

        with eng.connect as con:
            find_user = """
            SELECT *
            FROM Users
            WHERE username = """ + usernameLogin + """;
            """

            user = con.execute(find_user)

        if user is None or user == "":
            error = 'Username Not Found'
            return render_template('login.html', error=error)
        else:
            if sha256_crypt.verify(password_candidate, user.password):
                session['logged_in'] = True
                session['username'] = user['username']
                session['userid'] = user['id']

                # now = datetime.now()

                with eng.connect as con:
                    con.execute(
                        "UPDATE Users SET loginTime = GETDATE() WHERE id = user['id']")

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

    with eng.connect as con:
        watchlistitem = """
            SELECT *
            FROM WatchList
            WHERE id = session['user_id']
        """

        userwatchlist = con.execute(watchlistitem)

    # userwatchlist = WatchList.query.filter_by(user_id = session['userid']).all()
    stocks = []
    # details = []

    for item in userwatchlist:
        with eng.connect as con:
            comp = """
                SELECT *
                FROM Stocks
                WHERE id = item['stockID']
            """

            addstock = con.execute(comp)
        # addstock = StockInfo.query.filter_by(id=item.stockinfo_id).first()
            stocks.append(addstock)

    # for item in stocks:
    #     addDetails = StockPriceDetails.query.filter_by(
    #         stock_id=item.id).first()
    #     details.append(addDetails)

    if len(stocks) == 0:
        error = 'You are not tracking any stocks'
        return render_template('dashboard.html', error=error, stocks=stocks)
    else:
        return render_template('dashboard.html', stocks=stocks)
    return render_template('dashboard.html', stocks=stocks)


if __name__ == '__main__':
    app.run(debug=True)
