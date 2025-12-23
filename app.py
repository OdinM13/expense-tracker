import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    balance()
    return balance()


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    elif request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if stock is None:
            return apology("Invalid stock symbol", 400)

        try:
            shares = int(request.form.get("shares"))
            if shares < 1:
                return apology("Enter positive number of shares", 400)
        except ValueError:
            return apology("Enter positive number of shares", 400)

        sub_total = stock["price"] * shares
        total_old = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        if sub_total <= total_old[0]["cash"]:
            date_time = datetime.now()
            transaction_date = date_time.strftime("%Y-%m-%d %H:%M:%S")
            new_balance = total_old[0]["cash"] - sub_total
            db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, session["user_id"])
            db.execute(
                "INSERT INTO transactions (user_id, symbol, shares, price, date, type) VALUES (?, ?, ?, ?, ?, ?)",
                session["user_id"], stock["symbol"], shares, stock["price"], transaction_date, "bought"
            )
            balance()
            return balance()
        else:
            return apology("Not enough funds. Consider selling stock(s) to free cash.", 400)

def balance():
    rows = db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id = ? ORDER BY symbol", session["user_id"])

    stocks = []

    for row in rows:
        shares_total = sharecount(session["user_id"], row["symbol"])

        if shares_total > 0:
            symbol = row["symbol"]
            current_price = lookup(row["symbol"])
            current_price = current_price["price"]
            sub_total = shares_total * current_price
            form_sub_total = usd(sub_total)
            information = {"symbol": symbol, "shares": shares_total, "price": usd(current_price), "total": sub_total, "form_total": form_sub_total}
            stocks.append(information)

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash = cash[0]["cash"]
    new_total = 0

    for stock in stocks:
        new_total += stock["total"]
    total = cash + new_total

    return render_template("index.html", stocks=stocks, cash=usd(cash), total=usd(total))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT symbol, shares, price, date, type FROM transactions WHERE user_id = ? ORDER BY date DESC", session["user_id"])

    stocks = []

    for row in rows:
        information = {"symbol": row["symbol"], "shares": row["shares"], "price": usd(row["price"]), "date": row["date"], "type": row["type"]}
        stocks.append(information)

    return render_template("history.html", stocks=stocks)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
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
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        if not request.form.get("symbol"):
            return apology("provide symbol", 400)

        symbol = request.form.get("symbol")
        stock = lookup(symbol.upper())
        if stock is None:
            return apology("invalid symbol", 400)

        return render_template("quoted.html", stock=stock["name"], symbol=stock["symbol"], price=usd(stock["price"]))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    elif request.method == "POST":

        name = request.form.get("username")
        if not name:
            return apology("must provide username", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", name)

        if len(rows) == 1:
            return apology("User already exists", 400)

        password_unhashed = request.form.get("password")
        if not password_unhashed:
            return apology("must provide a password", 400)

        confirmation = request.form.get("confirmation")
        if not confirmation:
            return apology("must confirm password", 400)

        if password_unhashed != confirmation:
            return apology("Passwords don't match. Please try again", 400)
        else:
            hash = generate_password_hash(password_unhashed)
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", name, hash)

            login()
            return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        rows = db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id = ? ORDER BY symbol", session["user_id"])

        stocks = []

        for row in rows:
            shares_total = sharecount(session["user_id"], row["symbol"])

            if shares_total > 0:
                symbol = row["symbol"]
                stocks.append(symbol)

        return render_template("sell.html", stocks=stocks)

    elif request.method == "POST":
        if request.form.get("symbol") == None:
            return apology("must select a symbol", 400)

        stock = lookup(request.form.get("symbol"))

        try:
            shares = int(request.form.get("shares"))
            if shares < 1:
                return apology("Enter positive number of shares", 400)
        except ValueError:
            return apology("Enter positive number of shares", 400)

        rows = db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id = ? ORDER BY symbol", session["user_id"])

        for row in rows:
            shares_total = sharecount(session["user_id"], row["symbol"])

        if shares > shares_total:
            return apology("Not enough stocks in portfolio.", 400)
        else:
            sub_total = stock["price"] * shares
            total_old = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            #if sub_total <= total_old[0]["cash"]:
            date_time = datetime.now()
            transaction_date = date_time.strftime("%Y-%m-%d %H:%M:%S")
            new_balance = total_old[0]["cash"] + sub_total
            db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, session["user_id"])
            db.execute(
                "INSERT INTO transactions (user_id, symbol, shares, price, date, type) VALUES (?, ?, ?, ?, ?, ?)",
                session["user_id"], stock["symbol"], shares, stock["price"], transaction_date, "sold"
            )
            balance()
            return balance()

def sharecount(user_id, symbol):
    shares_total_bought = db.execute("SELECT SUM(shares) FROM transactions WHERE user_id = ? AND symbol = ? AND type = ?", user_id, symbol, 'bought')
    if shares_total_bought and shares_total_bought[0]["SUM(shares)"] is not None:
        shares_total_bought_value = shares_total_bought[0]["SUM(shares)"]
    else:
        shares_total_bought_value = 0

    shares_total_sold = db.execute("SELECT SUM(shares) FROM transactions WHERE user_id = ? AND symbol = ? AND type = ?", user_id, symbol, 'sold')
    if shares_total_sold and shares_total_sold[0]["SUM(shares)"] is not None:
        shares_total_sold_value = shares_total_sold[0]["SUM(shares)"]
    else:
        shares_total_sold_value = 0

    shares_total = shares_total_bought_value - shares_total_sold_value

    return shares_total


@app.route("/charge", methods=["GET", "POST"])
@login_required
def charge():
    """Charge account with more money"""
    if request.method == "GET":
        return render_template("charge.html")

    elif request.method == "POST":
        raw_money = request.form.get("money_raw")
        if not raw_money:
            return apology("Enter positive dollar amount", 403)

        try:
            money = float(raw_money)
            if money <= 0:
                return apology("Enter positive dollar amount", 403)
        except ValueError:
            return apology("Enter positive dollar amount", 403)

        total_old = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        new_balance = total_old[0]["cash"] + money

        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, session["user_id"])

        balance()
        return balance()
