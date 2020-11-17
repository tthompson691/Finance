import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "GET":
        """Show portfolio of stocks"""
        #return table of all transactions done by user
        userHistory = db.execute("SELECT symbol, shares, type FROM transactions WHERE id = :user_id", user_id = session["user_id"])

        #extract username
        username = db.execute("SELECT username FROM users WHERE id = :user_id", user_id=session["user_id"])
        username = username[0]["username"]

        #get user's available cash and convert to usd
        userCash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
        startCash = float(userCash[0]["cash"])
        dollars = usd(startCash)

        # print(userHistory)
        totals = {}
        stocks = []

        for action in userHistory:
            stock = action['symbol']
            shares = action['shares']

            # create dict of total number of each stock user owns
            if stock not in stocks:
                stocks.append(stock)
                totals[stock] = shares
            else:
                if action['type'] == "BUY":
                    totals[stock] += shares
                else:
                    totals[stock] -= shares

        # now create list of dicts, simulating a table with all relevant info (stock, shares, current price, total worth)
        portfolio = []
        netWorth = 0;

        for item in totals:
            quote = lookup(item)
            price = float(quote["price"])
            totalValue = price * totals[item]
            netWorth += totalValue

            portfolio.append({'stock': item, 'shares': totals[item], 'current_price': usd(price), 'total_value': usd(totalValue)})

        totalPValue = usd(netWorth + startCash)

        # print(portfolio)
        return render_template("index.html", username = username, portfolio=portfolio, netWorth=usd(netWorth), cash=dollars, totalPValue=totalPValue)
    # this condition activates if user clicks a button to buy/sell a stock they currently lown
    # else:



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    userCash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])

    # userCash returns as a single dict in a list, so let's extract the key value for just the number
    # and use a helper function to format it as USD
    # 'cash' variable used as a float, 'dollars' used as USD formatted string
    startCash = float(userCash[0]["cash"])
    dollars = usd(startCash)



    if request.method == "GET":
        return render_template("buy.html", userCash=dollars)
    else:
        symbol = request.form.get("symbol")

        quote = lookup(symbol)
        # make sure user filled out the symbol field, and that the symbol exists
        if not symbol:
            return apology("Gotta tell me what to buy, big guy")

        if not quote:
            return apology("Can't buy a nonexistent stock, big guy")


        try:
            shares = float(request.form.get("shares"))
        except:
            return apology("numbers, my dude")
        # make sure user put a positive integer for shares
        if not shares:
            return apology("Gotta tell me how much of that to buy, big guy")

        if shares.is_integer() == False:
            return apology("No fractions of shares, big guy")

        if shares <= 0:
            return apology("Think you're being cheeky, huh?")



        price = float(quote["price"])

        # calculate price of buy action
        buyPrice = price * shares

        # reject buy action if user doesn't have enough cash
        if buyPrice > startCash:
            return apology("lol you're too poor for that")

        # calculate new user cash
        endCash = startCash - buyPrice

        # update users database with new cash remaining value
        db.execute("UPDATE users SET cash = :endcash WHERE id = :user_id", endcash=endCash, user_id=session["user_id"])

        # update transactions table with all the relevant info

        # datetime (todo)
        now = datetime.now()

        # user id
        user_id = session["user_id"]

        # type (always buy within this function)
        transType = "BUY"

        # username
        username = db.execute("SELECT username FROM users WHERE id = :user_id", user_id=user_id)

        username = username[0]["username"]

        # make sure symbol is uppercase

        symbol = symbol.upper()

        db.execute("INSERT INTO transactions (date, id, username, symbol, price, type, shares, total_cost, start_cash, end_cash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            now, user_id, username, symbol, price, transType, shares, buyPrice, startCash, endCash)

        return redirect("/")



@app.route("/history")
@login_required
def history():

    userHistory = db.execute("SELECT date, symbol, shares, type, price FROM transactions WHERE id = :user_id", user_id = session["user_id"])

    # convert prices to USD
    for item in userHistory:
        item["price"] = usd(item["price"])

    print(userHistory)

    return render_template("history.html", userHistory=userHistory)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")

        # use helper function to query the IEX API
        quote = lookup(symbol)

        if not quote:
            return apology("Your stock symbol doesn't exist.")
        else:
            return render_template("quoted.html", symbol=symbol, quote=quote)

    #return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        # try/except structure will catch non-unique usernames
        try:
            username = request.form.get("username")
            if not username:
                return apology("Pick a username; preferrably something cringy that you will have nightmares about in 5-7 years.")

            password = request.form.get("password")
            if not password:
                return apology("Pick a password; preferrably something with as few characters of as little variety as possible.")

            check_password = request.form.get("check_password")

            if password != check_password:
                return apology("Passwords don't match you stupid bimblyboy")

            #will only get this far if input data has been validated
            pw_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username = username, hash = pw_hash)

            return redirect("/")

        except RuntimeError:
            return apology("How original. That username is taken.")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":

        return render_template("sell.html")

    else:
        #return table of all transactions done by user
        userHistory = db.execute("SELECT symbol, shares, type FROM transactions WHERE id = :user_id", user_id = session["user_id"])

        #extract username
        username = db.execute("SELECT username FROM users WHERE id = :user_id", user_id=session["user_id"])
        username = username[0]["username"]

        #get user's available cash and convert to usd
        userCash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
        startCash = float(userCash[0]["cash"])
        dollars = usd(startCash)

        # print(userHistory)
        totals = {}
        stocks = []

        for action in userHistory:
            stock = action['symbol']
            shares = action['shares']

            # create dict of total number of each stock user owns
            if stock not in stocks:
                stocks.append(stock)
                totals[stock] = shares
            else:
                if action['type'] == "BUY":
                    totals[stock] += shares
                else:
                    totals[stock] -= shares

        symbol = request.form.get("symbol")
        try:
            soldShares = int(request.form.get("shares"))
        except:
            return apology("Whole numbers only homie")

        if not symbol:
            return apology("Can't sell nothing, my dude")

        if symbol not in stocks:
            return apology("How you plan on selling something you don't own there?")

        if soldShares <= 0:
            return apology("Think you're cheeky, huh?")

        if soldShares > totals[symbol]:
            correctionStr = ("You only have " + str(totals[symbol]) + " shares of " + str(symbol) + ", big guy")
            return apology(correctionStr)

        # now that we've verified the meta of the transaction, let's actually execute it
        # first get a current quote of the stock price
        quote = lookup(symbol)

        price = float(quote["price"])

        sellPrice = soldShares * price


        # update user's available cash
        endCash = startCash + sellPrice

        db.execute("UPDATE users SET cash = :endcash WHERE id = :user_id", endcash=endCash, user_id=session["user_id"])

        # update transactions table
        now = datetime.now()

        # user id
        user_id = session["user_id"]

        # type (always sell within this function)
        transType = "SELL"

        # username
        username = db.execute("SELECT username FROM users WHERE id = :user_id", user_id=user_id)

        username = username[0]["username"]

        # uppercase symbol

        symbol = symbol.upper()

        db.execute("INSERT INTO transactions (date, id, username, symbol, price, type, shares, total_cost, start_cash, end_cash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            now, user_id, username, symbol, price, transType, soldShares, sellPrice, startCash, endCash)

        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
