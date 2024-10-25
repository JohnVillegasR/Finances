import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

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
    contracts = db.execute("SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total_shares > 0", user_id=session["user_id"])

    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]["cash"]

    totalvalue = cash
    total = cash

    for contract in contracts:
        quote = lookup(contract["symbol"])
        contract["name"] = quote["name"]
        contract["price"] = quote["price"]
        contract["value"] = contract["price"] * contract["total_shares"]
        totalvalue += contract["value"]
        total += contract["value"]

    return render_template("index.html", contracts= contracts, cash=usd(cash), totalvalue=usd(totalvalue), total=usd(total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method =="POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        if not symbol:
            return apology("symbol needed")
        elif not shares or not shares.isdigit() or int(shares) <= 0 :
            return apology("please input a positive integer")

        quote = lookup(symbol)
        if quote is None:
            return apology("No such symbol is found")

        price = quote["price"]
        total_cost = int(shares) * price
        cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id= session["user_id"])[0]["cash"]

        if cash < total_cost:
            return apology("more cash needed")

        db.execute("UPDATE users SET cash = cash - :total_cost WHERE id = :user_id", total_cost =  total_cost, user_id=session["user_id"])

        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)", user_id=session["user_id"], symbol=symbol, shares= shares, price=price)


        flash(f"bought {shares} shares of {symbol} for {usd (int(total_cost) / int(shares))} in total {usd(total_cost)}!")
        return redirect("/")
    else:
        return render_template("buy.html")




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("""SELECT CASE WHEN shares < 0 THEN 'SELL' ELSE 'BUY' END AS type, symbol, shares, price, shares * price AS total, time
            FROM transactions WHERE user_id = :user_id ORDER BY time DESC""", user_id=session["user_id"])

    return render_template("history.html", history=history)


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
        lines = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(lines) != 1 or not check_password_hash(lines[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = lines[0]["id"]

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
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if not quote:
            return apology("no such a quote", 400)
        return render_template("quote.html", name = quote["name"], quote=quote)
    else:
        return render_template("quote.html")





@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "POST":
        """ask the username, password, and confirmation"""
        if not request.form.get("username"):
            return apology("must type a usernam", 400)
        elif not request.form.get("password"):
            return apology("must type a password", 400)
        elif not request.form.get("confirmation"):
            return apology("must confirm your password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must type the same password", 400)

        rows = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 0:
            return apology("username already exists", 400)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))

        lines = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))

        session["user_id"] = lines[0]["id"]

        return redirect("/register")
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks = db.execute("SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id= :user_id GROUP BY symbol having total_shares > 0", user_id=session["user_id"])

    if request.method == 'POST':
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        if not symbol:
            return apology("Symbol needed")
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("need to input posotive number of shares")
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
                    sales_total= shares * price

                    db.execute("UPDATE users SET cash = cash + :sales_total WHERE id = :user_id", sales_total = sales_total, user_id=session["user_id"])

                    db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)", user_id= session["user_id"], symbol= symbol, shares=- shares, price=price)

                    return redirect("/")



        return apology("symbol doesn't exist")
    else:
        return render_template("sell.html", stocks=stocks)
