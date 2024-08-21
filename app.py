import os
import re

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, mock_lookup

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
    user_id = session["user_id"]
    portfolio = db.execute(
        "SELECT symbol, shares FROM portfolio WHERE user_id = :user_id", user_id=user_id)

    # Fetch current prices for each stock
    stocks = []
    for stock in portfolio:
        symbol = stock["symbol"]
        shares = stock["shares"]
        stock_info = lookup(symbol)
        if stock_info:
            stocks.append({
                "symbol": symbol,
                "shares": shares,
                "price": stock_info["price"],
                "total": shares * stock_info["price"]
            })

    # Calculate total portfolio value
    total_value = sum(stock["total"] for stock in stocks)

    return render_template("index.html", stocks=stocks, total_value=total_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Ensure symbol was entered
        if not symbol:
            return apology("must provide symbol", 400)

        # Ensure shares was entered and is a positive integer
        try:
            shares = int(shares)
            if shares <= 0:
                return apology("must provide positive number for shares", 400)
        except ValueError:
            return apology("must provide positive integer for shares", 400)

        stock = lookup(symbol.upper())
        if stock is None:
            return apology("Invalid symbol", 400)

        price = stock["price"]
        total = shares * price
        user_id = session["user_id"]

        # Fetch user's cash balance
        cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=user_id)[0]["cash"]
        if cash < total:
            return apology("Cash is not enough")

        # Update user's cash balance
        db.execute("UPDATE users SET cash = cash - :total WHERE id = :user_id",
                    total=total, user_id=user_id)

        # Insert transaction into transactions table
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)",
                   user_id=user_id, symbol=symbol, shares=shares, price=price)

        # Update user's portfolio
        db.execute("INSERT INTO portfolio (user_id, symbol, shares) VALUES (:user_id, :symbol, :shares) "
                   "ON CONFLICT(user_id, symbol) DO UPDATE SET shares = shares + :shares",
                   user_id=user_id, symbol=symbol, shares=shares)

        flash(f"Bought {shares} shares of {symbol} for {usd(total)}!")

        return redirect("/")
    else:
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = db.execute(
        "SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id = :user_id ORDER BY timestamp DESC", user_id=user_id)

    # Prepare the transactions for display
    history = []
    for transaction in transactions:
        history.append({
            "symbol": transaction["symbol"],
            "shares": transaction["shares"],
            "price": transaction["price"],
            "timestamp": transaction["timestamp"]
        })

    return render_template("history.html", transactions=history)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    if request.method == "POST":
        symbol = request.form.get("symbol")
        print(f"symbol: {symbol}")  # Debugging line

        if not symbol:
            return apology("Must provide symbol", 400)

        stock = lookup(symbol.upper())
        # print(f"stock: {stock}")  # Debugging line

        if stock is None:
            return apology("Invalid symbol", 400)

        return render_template("quoted.html", stock=stock)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not confirmation:
            return apology("must confirm your password", 400)

        # Ensure password and confirmation match
        elif password != confirmation:
            return apology("password and confirmation are not the same", 400)

        # Ensure password length is at least 8 characters
        elif len(password) < 8:
            return apology("password should be at least 8 characters", 400)

        # Ensure password contains at least 1 number
        elif not re.search(r'\d', password):
            return apology("password should contain at least 1 number", 403)

        # Ensure password contains at least 1 special character
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return apology("password should contain at least 1 special character", 403)

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Check if username already exists
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return apology("username already exists", 400)

        # Insert the new user into the database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hashed_password)

        # Fetch the new user's ID
        rows = db.execute("SELECT id FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "GET":
        # Fetch user's stocks
        stocks = db.execute(
            "SELECT symbol, SUM(shares) as total FROM transactions WHERE user_id = :user_id GROUP BY symbol", user_id=user_id)
        return render_template("sell.html", stocks=stocks)

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        # Ensure symbol was entered
        if not symbol:
            return apology("must provide symbol", 403)

        # Ensure shares was entered and is a positive number
        elif not shares or shares <= 0:
            return apology("must provide positive number for shares", 403)

        # Fetch the user's shares for the given symbol
        user_shares = db.execute("SELECT SUM(shares) as total FROM transactions WHERE user_id = :user_id AND symbol = :symbol GROUP BY symbol",
                                 user_id=user_id, symbol=symbol)[0]["total"]

        # Ensure the user has enough shares to sell
        if shares > user_shares:
            return apology("not enough shares", 403)

        # Fetch current stock price
        stock = lookup(symbol.upper())
        if stock is None:
            return apology("Invalid symbol", 403)

        price = stock["price"]
        total = shares * price

        # Update user's cash balance
        db.execute("UPDATE users SET cash = cash + :total WHERE id = :user_id",
                    total=total, user_id=user_id)

        # Insert transaction into transactions table
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)",
                   user_id=user_id, symbol=symbol, shares=-shares, price=price)

        # Update user's portfolio
        db.execute("UPDATE portfolio SET shares = shares - :shares WHERE user_id = :user_id AND symbol = :symbol",
                   shares=shares, user_id=user_id, symbol=symbol)

        # Remove stock from portfolio if shares become zero
        db.execute("DELETE FROM portfolio WHERE user_id = :user_id AND symbol = :symbol AND shares = 0",
                   user_id=user_id, symbol=symbol)

        flash(f"Sold {shares} shares of {symbol} for {usd(total)}!")

        return redirect("/")

    return redirect("/sell")


@app.route("/trade", methods=["POST"])
@login_required
def trade():
    """Handle buying and selling of stocks"""
    user_id = session["user_id"]
    symbol = request.form.get("symbol")
    action = request.form.get("action")
    shares = request.form.get("shares")

    # Debugging: Print the values of symbol, shares, and action
    print(f"Symbol: {symbol}, Shares: {shares}, Action: {action}")

    # Ensure symbol was entered and is not the default select option
    if not symbol:
        print("Apology: must provide symbol")
        return apology("must provide symbol", 403)

    # Ensure action was selected
    if not action or action == "__Select__":
        print("Apology: must select an action")
        return apology("must select an action", 403)

    # Ensure shares was entered and is a positive number
    try:
        shares = int(shares)
        if shares <= 0:
            print("Apology: must provide positive number for shares")
            return apology("must provide positive number for shares", 403)
    except (TypeError, ValueError):
        print("Apology: must provide positive number for shares")
        return apology("must provide positive number for shares", 403)

    # Fetch current stock price
    stock = lookup(symbol.upper())
    if stock is None:
        print("Apology: Invalid symbol")
        return apology("Invalid symbol", 403)

    price = stock["price"]
    total = shares * price

    try:
        if action == "buy":
            # Fetch user's cash balance
            cash = db.execute("SELECT cash FROM users WHERE id = :user_id",
                              user_id=user_id)[0]["cash"]
            if cash < total:
                print("Apology: Cash is not enough")
                return apology("Cash is not enough")

            # Update user's cash balance
            db.execute("UPDATE users SET cash = cash - :total WHERE id = :user_id",
                        total=total, user_id=user_id)

            # Insert transaction into transactions table
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)",
                       user_id=user_id, symbol=symbol, shares=shares, price=price)

            # Update user's portfolio
            db.execute("INSERT INTO portfolio (user_id, symbol, shares) VALUES (:user_id, :symbol, :shares) "
                       "ON CONFLICT(user_id, symbol) DO UPDATE SET shares = shares + :shares",
                       user_id=user_id, symbol=symbol, shares=shares)

            flash(f"Bought {shares} shares of {symbol} for {usd(total)}!")

        elif action == "sell":
            # Fetch the user's shares for the given symbol
            user_shares = db.execute("SELECT SUM(shares) as total FROM transactions WHERE user_id = :user_id AND symbol = :symbol GROUP BY symbol",
                                     user_id=user_id, symbol=symbol)[0]["total"]

            # Ensure the user has enough shares to sell
            if shares > user_shares:
                print("Apology: not enough shares")
                return apology("not enough shares", 403)

            # Update user's cash balance
            db.execute("UPDATE users SET cash = cash + :total WHERE id = :user_id",
                        total=total, user_id=user_id)

            # Insert transaction into transactions table
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)",
                       user_id=user_id, symbol=symbol, shares=-shares, price=price)

            # Update user's portfolio
            db.execute("UPDATE portfolio SET shares = shares - :shares WHERE user_id = :user_id AND symbol = :symbol",
                       shares=shares, user_id=user_id, symbol=symbol)

            # Remove stock from portfolio if shares become zero
            db.execute("DELETE FROM portfolio WHERE user_id = :user_id AND symbol = :symbol AND shares = 0",
                       user_id=user_id, symbol=symbol)

            flash(f"Sold {shares} shares of {symbol} for {usd(total)}!")

    except Exception as e:
        print(f"Apology: An error occurred: {e}")
        return apology(f"An error occurred: {e}", 500)

    return redirect("/")
