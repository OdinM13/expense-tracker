import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

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
    """Dashboard: Show balance, list and chart data for the current month"""
    user_id = session["user_id"]
    
    # Get user's current cash balance
    user_rows = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = user_rows[0]["cash"]

    # Fetch all expenses for the list (ordered by most recent)
    expenses = db.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", user_id)

    # Calculate total spent in the CURRENT month
    # 'start of month' ensures we only sum values from the 1st of this month onwards
    total_spent_query = db.execute(
        "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND date >= date('now', 'start of month')", 
        user_id
    )
    total_spent = total_spent_query[0]["total"] if total_spent_query[0]["total"] else 0

    # Fetch chart data: Grouped by category for the CURRENT month
    chart_rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? AND date >= date('now', 'start of month') "
        "GROUP BY category", 
        user_id
    )
    
    # Prepare lists for Chart.js
    chart_labels = [row["category"] for row in chart_rows]
    chart_values = [row["total"] for row in chart_rows]

    return render_template("index.html", 
                           cash=usd(cash), 
                           expenses=expenses, 
                           total_spent=usd(total_spent),
                           labels=chart_labels, 
                           values=chart_values)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Record a new expense"""
    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        description = request.form.get("description")

        # Basic validation
        if not amount or not category:
            return apology("must provide amount and category", 400)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return apology("amount must be positive", 400)
        except ValueError:
            return apology("invalid amount", 400)

        # Check if user has enough cash
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        if amount > user_cash:
            return apology("not enough funds", 400)

        # Insert expense and update user cash
        db.execute("INSERT INTO expenses (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
                   session["user_id"], amount, category, description)
        
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", amount, session["user_id"])

        flash("Expense added!")
        return redirect("/")
    
    else:
        categories = ["Food", "Rent", "Leisure", "Transport", "Subscription", "Other"]
        return render_template("add.html", categories=categories)


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    """Delete an expense and refund the cash"""
    expense_id = request.form.get("id")
    
    if not expense_id:
        return apology("missing expense ID", 400)

    # Get expense details for refund
    expense = db.execute("SELECT amount FROM expenses WHERE id = ? AND user_id = ?", 
                         expense_id, session["user_id"])
    
    if not expense:
        return apology("expense not found", 404)

    # Refund cash and delete record
    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", expense[0]["amount"], session["user_id"])
    db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", expense_id, session["user_id"])

    flash("Expense deleted!")
    return redirect("/")


@app.route("/charge", methods=["GET", "POST"])
@login_required
def charge():
    """Add funds to account"""
    if request.method == "POST":
        amount = request.form.get("money_raw")
        
        if not amount:
            return apology("must provide amount", 400)
            
        try:
            amount = float(amount)
            if amount <= 0:
                return apology("must be positive amount", 400)
        except ValueError:
            return apology("invalid amount", 400)

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", amount, session["user_id"])
        
        flash("Funds added!")
        return redirect("/")
    else:
        return render_template("charge.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password"):
            return apology("must provide username and password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or password != confirmation:
            return apology("check username and passwords", 400)

        hash = generate_password_hash(password)
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        except:
            return apology("username already exists", 400)

        return redirect("/login")
    else:
        return render_template("register.html")
