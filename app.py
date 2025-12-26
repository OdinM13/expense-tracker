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
    """Dashboard: Show cash flow, analytics and transaction history"""
    user_id = session["user_id"]
    timespan = request.args.get("filter", "month")

    # Define SQL filters based on time horizon
    if timespan == "week":
        date_filter = "date >= date('now', '-7 days')"
        display_title = "Last 7 Days"
    elif timespan == "all":
        date_filter = "1=1"
        display_title = "All Time"
    else:
        date_filter = "date >= date('now', 'start of month')"
        display_title = "This Month"

    # 1. Fetch current balance
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    # 2. Fetch combined history (Expenses and Income) using UNION
    # We add a virtual column 'type' to distinguish between them in the template
    transactions = db.execute(
            f"SELECT id, amount, category, description, date, 'expense' AS type FROM expenses "
            f"WHERE user_id = ? AND {date_filter} "
            f"UNION ALL "
            f"SELECT id, amount, 'Deposit' AS category, 'Cash Inflow' AS description, date, 'income' AS type FROM income "
            f"WHERE user_id = ? AND {date_filter} "
            f"ORDER BY date DESC", user_id, user_id
            )

    # 3. Calculate Totals for the selected period
    total_spent = db.execute(f"SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND {date_filter}", user_id)[0]["total"] or 0
    total_income = db.execute(f"SELECT SUM(amount) AS total FROM income WHERE user_id = ? AND {date_filter}", user_id)[0]["total"] or 0

    # 4. Data for Category Chart (Expenses only)
    chart_rows = db.execute(
            f"SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? AND {date_filter} GROUP BY category", 
            user_id
            )
    cat_labels = [row["category"] for row in chart_rows]
    cat_values = [row["total"] for row in chart_rows]

    # 5. Data for Trend Chart (Income vs. Expenses over time)
    # Get daily expenses
    exp_trend = db.execute(
            f"SELECT date(date) AS day, SUM(amount) AS total FROM expenses "
            f"WHERE user_id = ? AND {date_filter} GROUP BY day ORDER BY day ASC", user_id
            )
    # Get daily income
    inc_trend = db.execute(
            f"SELECT date(date) AS day, SUM(amount) AS total FROM income "
            f"WHERE user_id = ? AND {date_filter} GROUP BY day ORDER BY day ASC", user_id
            )

    return render_template("index.html", 
                           cash=usd(cash), 
                           transactions=transactions, 
                           total_spent=usd(total_spent),
                           total_income=usd(total_income),
                           cat_labels=cat_labels, 
                           cat_values=cat_values,
                           exp_trend=exp_trend,
                           inc_trend=inc_trend,
                           timespan=timespan,
                           display_title=display_title)

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
    """Add funds and log the transaction"""
    if request.method == "POST":
        amount = request.form.get("money_raw")
        if not amount or float(amount) <= 0:
            return apology("Invalid amount", 400)

        amount = float(amount)
        # 1. Update user's main balance
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", amount, session["user_id"])
        # 2. Log the deposit in the income table
        db.execute("INSERT INTO income (user_id, amount) VALUES (?, ?)", session["user_id"], amount)

        flash("Funds added successfully!")
        return redirect("/")
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
