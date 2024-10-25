import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Confure application
app = Flask(__name__)

# Custom filte
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Path tothe SQLite database
DATABASE = 'finance.db'

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection."""
    db = getattr(session, '_database', None)
    if db is not None:
        db.close()

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
    db = get_db()
    cursor = db.cursor()
    
    # Get the curret stock holdings
    contracts = cursor.execute(
        "SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0", 
        (session["user_id"],)
    ).fetchall()

    # Get the user's available cash
    cash = cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],)).fetchone()["cash"]

    totalvalue = cash
    total = cash

    # Add u the value of all holdings
    for contract in contracts:
        quote = lookup(contract["symbol"])
        contract["name"] = quote["name"]
        contract["price"] = quote["price"]
        contract["value"] = contract["price"] * contract["total_shares"]
        totalvalue += contract["value"]
        total += contract["value"]

    return render_template("index.html", contracts=contracts, cash=usd(cash), totalvalue=usd(totalvalue), total=usd(total))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        if not symbol:
            return apology("symbol needed")
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("please input a positive integer")

        quote = lookup(symbol)
        if quote is None:
            return apology("No such symbol is found")

        price = quote["price"]
        total_cost = int(shares) * price
        
        db = get_db()
        cursor = db.cursor()
        cash = cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],)).fetchone()["cash"]

        if cash < total_cost:
            return apology("more cash needed")

        # Update the use's cash balance and record the transaction
        cursor.execute("UPDATE users SET cash = cash - ? WHERE id = ?", (total_cost, session["user_id"]))
        cursor.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", 
                       (session["user_id"], symbol, shares, price))
        db.commit()

        flash(f"Bought {shares} shares of {symbol} for {usd(int(total_cost) / int(shares))} in total {usd(total_cost)}!")
        return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    db = get_db()
    cursor = db.cursor()
    history = cursor.execute("""
        SELECT CASE WHEN shares < 0 THEN 'SELL' ELSE 'BUY' END AS type, symbol, shares, price, 
               shares * price AS total, time 
        FROM transactions 
        WHERE user_id = ? 
        ORDER BY time DESC
    """, (session["user_id"],)).fetchall()

    return render_template("history.html", history=history)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        if not request.form.get("password"):
            return apology("must provide password", 403)

        db = get_db()
        cursor = db.cursor()
        lines = cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()

        if len(lines) != 1 or not check_password_hash(lines[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = lines[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if not quote:
            return apology("no such quote", 400)
        return render_template("quote.html", name=quote["name"], quote=quote)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must type a username", 400)
        elif not request.form.get("password"):
            return apology("must type a password", 400)
        elif not request.form.get("confirmation"):
            return apology("must confirm your password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must type the same password", 400)

        db = get_db()
        cursor = db.cursor()
        rows = cursor.execute("SELECT id FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()

        if len(rows) != 0:
            return apology("username already exists", 400)

        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", 
                       (request.form.get("username"), generate_password_hash(request.form.get("password"))))
        db.commit()

        lines = cursor.execute("SELECT id FROM users WHERE username = ?", (request.form.get("username"),)).fetchone()

        session["user_id"] = lines["id"]

        return redirect("/register")
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    db = get_db()
    cursor = db.cursor()
    stocks = cursor.execute(
        "SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0", 
        (session["user_id"],)
    ).fetchall()

    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        if not symbol:
            return apology("Symbol needed")
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("need to input a positive number of shares")
        else:
            shares = int(shares)

        for stock in stocks:
            if stock["symbol"] == symbol:
                if stock["total_shares"] < shares:
                    return apology("not enough shares")
                else:
                    quote = lookup(symbol)
                    if quote is None:
                        return apology("symbol doesn't exist")
                    price = quote["price"]
                    sales_total = shares * price

                    cursor.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (sales_total, session["user_id"]))
                    cursor.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", 
                                   (session["user_id"], symbol, -shares, price))
                    db.commit()

                    return redirect("/")

        return apology("symbol doesn't exist")
    else:
        return render_template("sell.html", stocks=stocks)
