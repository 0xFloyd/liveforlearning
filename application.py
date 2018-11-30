import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
application = app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.jinja_env.globals.update(lookup=lookup)

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


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    #current portfolio value
    portfolio = db.execute("SELECT stock, SUM(shares) as num_shares, price FROM transactions WHERE user = :userid GROUP BY stock", userid = session["user_id"])

    cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid=session["user_id"])
    current_cash = round(cash[0]["cash"], 2)
    current_portfolio_value = current_cash

    for x in portfolio:
        stock_shares = x["num_shares"]
        stock_price = x["price"]
        stock_value = stock_shares * stock_price
        current_portfolio_value += stock_value

    return render_template("index.html", current_cash = current_cash, portfolio = portfolio, current_portfolio_value = current_portfolio_value) #total_value = total_value


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        stock = lookup(request.form.get("symbol"))

        if stock == None:
            return apology("Invalid stock symbol", 400)

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("indicate positive number of shares", 400)

        if shares < 0:
                return apology("indicate number of shares", 400)

        current_cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid=session["user_id"])
        cash = current_cash[0]["cash"]
        cost_of_purchase = stock["price"] * shares

        if current_cash == None or cash < cost_of_purchase:
            return apology("Not enough cash on hand", 400)

        else:
            db.execute("UPDATE users SET cash = cash - :cost WHERE id = :userid", cost=cost_of_purchase, userid=session["user_id"])
            db.execute("INSERT INTO transactions (user, stock, shares, price) VALUES (:userid, :symbol, :shares, :price)", userid=session["user_id"], symbol = stock["symbol"], shares = shares, price = stock["price"])

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_transactions = db.execute("SELECT stock, shares, price, time FROM transactions WHERE user = :userid", userid = session["user_id"])
    #chronology of user's interactions
    # whether stock was bought/sold
    # stock symbol and purchase/sale price
    # shares bought or sold
    # date/time of transaction

    return render_template("history.html", user_transactions = user_transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

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
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
    #display form
    #retrieve stock quote
    #display stock quote

        stock = lookup(request.form.get("symbol"))

        if stock == None:
            return apology("Invalid stock symbol", 400)

        # Redirect user to home page
        return render_template("quoted.html", stock=stock)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was entered again
        elif not request.form.get("confirmation"):
            return apology("must provide password again", 400)

        #return apology if passwords don't match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        #encrpyt password
        hash = generate_password_hash(request.form.get("password"))
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=hash)

        if not result:
            return apology("username already exists", 400)

        else:
            return apology("Congratulations! You have been registered.", 200)

        # Remember which user has logged in
        session["user_id"] = result

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":

        # get current stock information
        stock = lookup(request.form.get("symbol"))

        if stock == None:
            return apology("Invalid stock symbol", 400)

        # check if shares is a number and if user entered a positive number
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("indicate positive number of shares to sell", 400)

        if shares < 1:
                return apology("indicate positive number of shares to sell", 400)

        #find how many shares are owned of stock selected to sell
        shares_owned = db.execute("SELECT SUM(shares) as num_shares FROM transactions WHERE user = :userid and stock = :symbol GROUP BY stock", userid = session["user_id"], symbol=request.form.get("symbol"))

        #check if user has enough shares to sell
        if shares > shares_owned[0]["num_shares"]:
            return apology("Sorry, you don't have that many shares to sell", 400)

        current_cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid=session["user_id"])
        cash = current_cash[0]["cash"]
        value_of_sale = stock["price"] * shares

        db.execute("UPDATE users SET cash = cash + :sell WHERE id = :userid", sell=value_of_sale, userid=session["user_id"])
        db.execute("INSERT INTO transactions (user, stock, shares, price) VALUES (:userid, :symbol, :shares, :price)", userid=session["user_id"], symbol = stock["symbol"], shares = -shares, price = stock["price"])

        return redirect("/")

    else:
        all_stocks = db.execute("SELECT stock, SUM(shares) as num_shares FROM transactions WHERE user = :userid GROUP BY stock", userid=session["user_id"])
        return render_template("sell.html", all_stocks=all_stocks)

@app.route("/funds", methods=["GET", "POST"])
@login_required
def funds():
    """Deposit/ Withdraw Account funds """

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        transaction = str(request.form.get("transaction"))

        if transaction == None:
            return apology("Please choose Withdraw or Deposit", 400)

        try:
            amount = int(request.form.get("amount"))
        except:
            return apology("indicate amount to deposit or withdraw", 400)

        if amount < 1:
                return apology("indicate amount to deposit or withdraw", 400)

        if transaction == "deposit":
            current_cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid=session["user_id"])
            db.execute("UPDATE users SET cash = cash + :add WHERE id = :userid", add=amount, userid=session["user_id"])

        elif transaction == "withdraw":
            current_cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid=session["user_id"])
            cash = current_cash[0]["cash"]
            if amount > cash:
                return apology("Insufficent funds", 400)

            else:
                db.execute("UPDATE users SET cash = cash - :withdraw WHERE id = :userid", withdraw=amount, userid=session["user_id"])

        else:
            return apology("Transaction failed", 400)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("funds.html")

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
