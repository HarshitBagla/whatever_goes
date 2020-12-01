from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField, DateField, DecimalField
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sys
import requests
from lxml import html
import pandas as pd
import yfinance as yf
import numpy as np 
import matplotlib.pyplot as plt
from pandas import DataFrame

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

    with eng.connect() as con:
        watchlistitem = """
            SELECT *
            FROM watchlistToStock
            WHERE watchListId = """+str(session['watchlistid'])+""";
        """

        userwatchlist = con.execute(watchlistitem)
        userwatchlist = userwatchlist.fetchall()

    stocks = []

    for item in userwatchlist:
        with eng.connect() as con:
            comp = """
                SELECT *
                FROM Stocks
                WHERE ticker = '"""+str(item[1])+"""';
            """

            addstock = con.execute(comp)
            addstock = addstock.first()
        stocks.append(addstock)

    if len(stocks) == 0:
        error = 'You are not tracking any stocks'
        return render_template('dashboard.html', error=error, stocks=stocks)
    else:
        return render_template('dashboard.html', stocks=stocks)
    return render_template('dashboard.html', stocks=stocks)

# Search Form


class SearchForm(Form):
    ticker = StringField('Ticker', [validators.DataRequired()])

# Route for Price page for top 10 price change in the market


@app.route('/prices', methods=['GET', 'POST'])
@is_logged_in
def prices():
    form = SearchForm(request.form)
    search = False
    if request.method == 'POST' and form.validate():
        ticker_input = form.ticker.data
        search = True

        with eng.connect() as con:
            searchticker = """
                SELECT *
                FROM Stocks
                WHERE ticker = '""" + str(ticker_input) + """';
            """

            prices = con.execute(searchticker)
            prices = prices.fetchall()
        
        with eng.connect() as con:
            countusers = """
                SELECT t.ticker, count(DISTINCT u.id) as total
                FROM Transactions t JOIN Users u ON t.userId=u.id
                WHERE ticker = '""" + str(ticker_input) + """'
                GROUP BY t.ticker;
            """

            numusers = con.execute(countusers)
            numusers = numusers.first()

        if len(prices) == 0:
            error = 'No such company found. Try again'
            with eng.connect() as con:
                searchticker = """
                    SELECT *
                    FROM Stocks;
                """

                prices = con.execute(searchticker)
                prices = prices.fetchall()
            search = False
            return render_template('prices.html', prices=prices, search=search, form=form, error=error)
        else:
            flash('Here are your search results', 'success')
            return render_template('prices.html', prices=prices, search=search,  numusers=numusers, form=form)
    with eng.connect() as con:
        searchticker = """
                SELECT *
                FROM Stocks;
            """

        prices = con.execute(searchticker)
        prices = prices.fetchall()
    return render_template('prices.html', prices=prices, search=search, form=form)

# For Tracking a Stock


@app.route('/track/<stockid>/')
def track(stockid):
    with eng.connect() as con:
        check = """
            SELECT *
            FROM watchlistToStock
            WHERE watchListId = """ + str(session['watchlistid']) + """ AND ticker = '""" + str(stockid) + """';
        """

        checking = con.execute(check)
        checking = checking.first()

    if checking == None:
        data = {
            "watchListId": session['watchlistid'],
            "ticker": stockid
        }
        with eng.connect() as con:
            inserstock = text(
                "INSERT INTO watchlistToStock (watchListId, ticker) VALUES (:watchListId, :ticker);")

            checking = con.execute(inserstock, **data)

        flash('Stock is now added to your watchlist', 'success')
    else:
        flash('Stock already added')

    return redirect(url_for('dashboard'))

# For Untracking the stock


@app.route('/untrack/<stockid>/')
def untrack(stockid):
    with eng.connect() as con:
        check = """
            DELETE
            FROM watchlistToStock
            WHERE watchListId = """ + str(session['watchlistid']) + """ AND ticker = '""" + str(stockid) + """';
        """

        checking = con.execute(check)

    flash('Stock removed from watchlist', 'success')

    return redirect(url_for('dashboard'))


@app.route('/transactions', methods=['GET', 'POST'])
@is_logged_in
def transactions():
    form = SearchForm(request.form)
    if request.method == 'POST' and form.validate():
        ticker_input = form.ticker.data

        with eng.connect() as con:
            searchtransactions = """
                SELECT *
                FROM Transactions
                WHERE ticker = '""" + str(ticker_input) + """' AND userId = """ + str(session['userid']) + """;
            """

            ts = con.execute(searchtransactions)
            ts = ts.fetchall()

        if len(ts) == 0:
            error = 'No such transactions found. Try again'
            with eng.connect() as con:
                searchtransactions = """
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
        searchtransactions = """
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
            "userId": session['userid']
        }

        with eng.connect() as con:
            search_ticker = """
                SELECT *
                FROM Stocks
                WHERE ticker = '""" + str(ticker) + """';
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

            flash(
                'Your Transaction has been added. Go to the Transaction tab to view it.', 'success')
            return render_template('add_transaction.html', form=form)

    return render_template('add_transaction.html', form=form)


@app.route('/delete_transaction/<int:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_transaction(id):
    if request.method:

        with eng.connect() as con:
            search_ticker = """
                DELETE FROM Transactions
                WHERE id = """ + str(id) + """;
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
            update_t = """
                UPDATE Transactions
                SET buyPrice = """ + str(buyPrice) + """, quantity = """ + str(quantity) + """
                WHERE id = """ + str(id) + """;
            """
            s = con.execute(update_t)

        flash('Your Transaction has been updated.', 'success')
        return redirect(url_for('transactions'))

    return render_template('update_transaction.html', form=form)

@app.route('/view_gainers', methods=['POST', 'GET'])
@is_logged_in
def view_gainers():
    currentTime = datetime.now()
    ct_str = currentTime.strftime("%Y-%m-%d")
    found = False
    res = None

    with eng.connect() as con:
        search = """
            SELECT ticker, volume
            FROM stock_gainers
            WHERE DATE(accesstime) = '""" + ct_str + """';
        """

        s = con.execute(search)
        s = s.fetchall()
        if len(s) != 0:
            found = True
            res = s
    ret_list = []
    if found:
        print("using database stored gain values")
        # print(res[0][0])
        # for x in res:
        #     ret_list.append([x[]])
        return render_template('view_gainers.html', data=res)
    
    ret_list = []
    r = requests.get("https://finance.yahoo.com/gainers")
    parser = html.fromstring(r.text)
    rows = parser.xpath('//tr[@class="simpTblRow Bgc($hoverBgColor):h BdB Bdbc($seperatorColor) Bdbc($tableBorderBlue):h H(32px) Bgc($lv2BgColor) "]')
    rows2 = parser.xpath('//tr[@class="simpTblRow Bgc($hoverBgColor):h BdB Bdbc($seperatorColor) Bdbc($tableBorderBlue):h H(32px) Bgc($lv1BgColor) "]')
    i = 0
    j = 0
    while i < len(rows) and j < len(rows2):
        if (i < len(rows)):
            elem = rows[i].xpath('.//a/text()')
            volumeRow = rows[i].xpath('//td[@aria-label="Volume"]')
            vol = volumeRow[(i* 2)].xpath('.//span[@class="Trsdu(0.3s) "]/text()')
            if vol[0].find('M') >= 0:
                ret_list.append([elem[0], vol[0]])
            i += 1
        if (j < len(rows)):
            elem = rows2[j].xpath('.//a/text()')
            volumeRow = rows2[j].xpath('//td[@aria-label="Volume"]')
            vol = volumeRow[(j * 2) + 1].xpath('.//span[@class="Trsdu(0.3s) "]/text()')

            if vol[0].find('M') >= 0:
                # print(vol[0])
                ret_list.append([elem[0], vol[0]])
            j += 1

    for x in ret_list:

        data = {
            "ticker": x[0],
            "volume": x[1],
            "accessTime": datetime.now(),
        }

        with eng.connect() as con:
            add_user = text("""
            INSERT INTO stock_gainers (ticker, volume, accessTime)
            VALUES (:ticker, :volume, :accessTime);
            """)

            exe = con.execute(add_user, **data)
    
    return render_template('view_gainers.html', data=ret_list)

class ShouldBuy(Form):
    ticker = StringField('ticker', [validators.DataRequired()])


from matplotlib.figure import Figure
import io
import base64
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

@app.route('/analysis', methods=['GET', 'POST'])
@is_logged_in
def analysis():
    form = ShouldBuy(request.form)

    if request.method == 'POST' and form.validate():
        t_data = form.ticker.data

        data = yf.Ticker(t_data)
        hist1mo = data.history(period="1mo")["Close"]
        hist6mo = data.history(period="6mo")["Close"]

        sma1mo = sum(hist1mo)/30
        sma6mo = sum(hist6mo)/180


        if sma1mo > sma6mo:
            flash("You should BUY based on Simple Moving Averages Cross Strategy", 'success')
        else:
            flash("You should SELL based on Simple Moving Averages Cross Strategy", 'error')
        

        #check if analysis run on same day and ticker already stored in database
        currentTime = datetime.now()
        ct_str = currentTime.strftime("%Y-%m-%d")
        found = False
        res = None

        with eng.connect() as con:
            search = """
                SELECT img
                FROM Images
                WHERE ticker = '""" + str(t_data) + """' AND DATE(accesstime) = '""" + ct_str + """';
            """

            s = con.execute(search)
            s = s.fetchall()

            if len(s) != 0:
                found = True
                res = s
        
        if found:
            print("using database stored image")
            # print(res[0][0])
            return render_template('analysis2.html', form=form, image=res[0][0])

        #if not found run anaylsis and store in databse
        
        #get 1mo SMA and 6mo SMA data lines
        data = yf.Ticker(t_data)

        #10d
        hist20d = data.history(period="2mo")["Close"]
        data_10d = []
        idx = 10
        for x in range(30):
            trim = hist20d[idx-10:idx]
            sm = sum(trim)
            data_10d.append(sm/10)
            idx += 1
        #2mo
        hist4mo = data.history(period="4mo")["Close"]
        data_2mo = []
        idx = 60
        for x in range(30):
            trim = hist4mo[idx-60:idx]
            sm = sum(trim)
            data_2mo.append(sm/60)
            idx += 1
            
            #When were good buy points

        data = yf.Ticker(t_data)
        hist1mo = data.history(period="1mo")["Close"]

        disp = hist1mo.to_frame()
        trim_10d = data_10d[30-len(hist1mo):]
        disp["10d-SMA"] = data_10d[30-len(hist1mo):]

        trim_2mo = data_2mo[-len(hist1mo):]
        disp["2mo-SMA"] = trim_2mo

        indexs=disp.index.values
        # print(x)

        #add markers
        markers = [0] * len(trim_2mo)

        for i in range(len(trim_2mo)):
            if trim_2mo[i] > trim_10d[i] and trim_2mo[i-1] <= trim_10d[i-1]:
                markers[i] = -1
            elif trim_2mo[i] < trim_10d[i] and trim_2mo[i-1] >= trim_10d[i-1]:
                markers[i] = 1
            else:
                markers[i] = 0
        markers_sell = [x for x in range(len(markers)) if markers[x] == -1]
        markers_buy = [x for x in range(len(markers)) if markers[x] == 1]
        
        #plot prices, SMA, and buy/sell points
        fig = Figure(figsize=(15,8))
        axis = fig.add_subplot(1, 1, 1)

        # axis.figure(figsize = (15,8))
        axis.plot(indexs, disp["Close"],'-rv',markevery =markers_sell, markersize=20, label="Sell Here")
        axis.plot(indexs, disp["Close"], '-g^',markevery =markers_buy, markersize=20, label="Buy Here")
        axis.plot(indexs, disp["Close"], color="purple")

        axis.plot(disp["10d-SMA"], label="10d-SMA")
        axis.plot(disp["2mo-SMA"], label="2mo-SMA")

        axis.grid()
        axis.set_ylabel("Price")

        axis.legend()
        axis.set_title('Previous Buying/Selling Points based on SMA Crossover')

        #Source: https://gitlab.com/snippets/1924163
        
        # Convert plot to PNG image
        pngImage = io.BytesIO()
        FigureCanvas(fig).print_png(pngImage)

        # Encode PNG image to base64 string
        pngImageB64String = "data:image/png;base64,"
        pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
        # print(pngImageB64String)

        data = {
            "ticker": t_data,
            "img": pngImageB64String,
            "accessTime": datetime.now(),
        }

        with eng.connect() as con:
            add_user = text("""
            INSERT INTO Images (ticker, img, accessTime)
            VALUES (:ticker, :img, :accessTime);
            """)

            exe = con.execute(add_user, **data)

        return render_template('analysis2.html', form=form, image=pngImageB64String)

    return render_template('analysis.html', form=form)

# Route for logout


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
