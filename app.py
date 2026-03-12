import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

if app.config.get("DEBUG"):
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

app.jinja_env.filters["usd"] = usd
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


def execute_db(query, *args, **kwargs):
    conn = sqlite3.connect("finance.db", timeout=10)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if kwargs:
        cur.execute(query, kwargs)
    else:
        cur.execute(query, args)
    
    if query.strip().upper().startswith("SELECT"):
        result = [dict(row) for row in cur.fetchall()]
    else:
        conn.commit()
        result = cur.lastrowid
        
    conn.close()
    return result

@app.route("/")
@login_required
def index():
    rows = execute_db(
        "SELECT symbol, SUM(shares) AS shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING shares > 0",
        session["user_id"]
    )

    holdings = []
    grand_total = 0

    for row in rows:
        quote = lookup(row["symbol"])
        price = quote["price"]
        total = row["shares"] * price
        grand_total += total

        holdings.append({
            "symbol": row["symbol"],
            "shares": row["shares"],
            "price": price,
            "total": total
        })

    cash = execute_db("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    grand_total += cash

    return render_template("index.html", holdings=holdings, cash=cash, total=grand_total)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)
        if not password:
            return apology("must provide password", 400)
        if password != confirmation:
            return apology("passwords do not match", 400)

        hash_pw = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            result = execute_db("INSERT INTO users (username, hash, cash) VALUES (:username, :hash, :cash)", username=username, hash=hash_pw, cash=10000)
        except sqlite3.IntegrityError:
            return apology("username already exists", 400)

        session["user_id"] = result
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            return apology("must provide username", 403)
        if not password:
            return apology("must provide password", 403)
        
        rows = execute_db("SELECT * FROM users WHERE username = :username", username=username)
        
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password", 403)
        
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol", 400)
        quote = lookup(symbol)
        if quote is None:
            return apology("invalid symbol", 400)
        return render_template("quoted.html", quote=quote)
    else:
        return render_template("quote.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares_str = request.form.get("shares")

        if not symbol:
            return apology("must provide symbol", 400)
        if not shares_str or not shares_str.isdigit() or int(shares_str) <= 0:
            return apology("must provide positive integer shares", 400)

        shares = int(shares_str)
        quote = lookup(symbol)
        if quote is None:
            return apology("invalid symbol", 400)

        price = quote["price"]
        total = shares * price

        user = execute_db("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = user[0]["cash"]

        if cash < total:
            return apology("can't afford", 400)

        execute_db("UPDATE users SET cash = cash - ? WHERE id = ?", total, session["user_id"])
        execute_db(
            "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            session["user_id"], symbol.upper(), shares, price
        )

        flash("Bought!")
        return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    rows = execute_db("SELECT symbol, SUM(shares) AS shares FROM transactions WHERE user_id = :uid GROUP BY symbol HAVING shares > 0", uid=user_id)
    symbols = [r["symbol"] for r in rows]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares_str = request.form.get("shares")
        
        if not symbol:
            return apology("must select symbol", 400)
        if symbol not in symbols:
            return apology("you do not own that stock", 400)
        if not shares_str or not shares_str.isdigit() or int(shares_str) <= 0:
            return apology("must provide positive integer shares", 400)
        
        shares = int(shares_str)
        own = execute_db("SELECT SUM(shares) AS shares FROM transactions WHERE user_id = :uid AND symbol = :symbol GROUP BY symbol", uid=user_id, symbol=symbol)
        owned = own[0]["shares"] if own else 0
        
        if shares > owned:
            return apology("too many shares", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("invalid symbol", 400)

        price = quote["price"]
        revenue = shares * price

        execute_db("UPDATE users SET cash = cash + :revenue WHERE id = :uid", revenue=revenue, uid=user_id)
        execute_db("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:uid, :symbol, :shares, :price)",
                   uid=user_id, symbol=symbol, shares=-shares, price=price)

        return redirect("/")
    else:
        return render_template("sell.html", symbols=symbols)

@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    rows = execute_db("SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id = :uid ORDER BY timestamp DESC", uid=user_id)
    for r in rows:
        r["type"] = "BUY" if r["shares"] > 0 else "SELL"
        r["shares_display"] = abs(r["shares"])
    return render_template("history.html", history=rows)

@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":
        amount_str = request.form.get("amount")
        try:
            amount = float(amount_str)
        except (TypeError, ValueError):
            return apology("invalid amount", 400)
        
        if amount <= 0:
            return apology("amount must be positive", 400)
        
        execute_db("UPDATE users SET cash = cash + :amt WHERE id = :uid", amt=amount, uid=session["user_id"])
        return redirect("/")
    else:
        return render_template("addcash.html")

@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
    if request.method == "POST":
        curr = request.form.get("current")
        new = request.form.get("new")
        confirm = request.form.get("confirm")
        
        if not curr or not new or not confirm:
            return apology("must fill fields", 400)
        if new != confirm:
            return apology("new passwords must match", 400)
            
        user = execute_db("SELECT hash FROM users WHERE id = :uid", uid=session["user_id"])
        
        if not check_password_hash(user[0]["hash"], curr):
            return apology("current password incorrect", 400)
            
        newhash = generate_password_hash(new, method='pbkdf2:sha256')
        execute_db("UPDATE users SET hash = :h WHERE id = :uid", h=newhash, uid=session["user_id"])
        return redirect("/")
    else:
        return render_template("changepassword.html")

if __name__ == '__main__':
    app.run(debug=True)