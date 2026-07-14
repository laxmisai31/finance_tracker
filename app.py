from collections import defaultdict
from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "finance_tracker_secret_key"

DATABASE = "finance.db"


# ---------------- DATABASE CONNECTION ---------------- #

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- CREATE DATABASE ---------------- #

def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        type TEXT,
        category TEXT,
        amount REAL,
        payment_method TEXT,
        description TEXT,
        status TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return redirect("/login")


# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        try:

            cursor.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, password)
            )

            conn.commit()
            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:

            conn.close()

            return "Username already exists."

    return render_template("register.html")


# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/dashboard")

        else:

            return "Invalid Username or Password"

    return render_template("login.html")


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],))

    transactions = cursor.fetchall()

    total_income = 0
    total_expense = 0

    category_data = defaultdict(float)
    monthly_data = defaultdict(float)

    for row in transactions:

        amount = float(row["amount"])

        if row["type"] == "Income":
            total_income += amount

        else:
            total_expense += amount
            category_data[row["category"]] += amount

        month = row["date"][:7]
        monthly_data[month] += amount

    balance = total_income - total_expense

    conn.close()

    return render_template(
        "dashboard.html",
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        category_labels=list(category_data.keys()),
        category_values=list(category_data.values()),
        monthly_labels=list(monthly_data.keys()),
        monthly_values=list(monthly_data.values())
    )
@app.route("/add", methods=["POST"])
def add_transaction():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO transactions(

    user_id,
    date,
    type,
    category,
    amount,
    payment_method,
    description,
    status

    )

    VALUES(?,?,?,?,?,?,?,?)

    """,

    (

    session["user_id"],

    request.form["date"],

    request.form["type"],

    request.form["category"],

    float(request.form["amount"]),

    request.form["payment_method"],

    request.form["description"],

    request.form["status"]

    ))

    conn.commit()

    conn.close()

    return redirect("/dashboard")


# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ---------------- RUN APPLICATION ---------------- #

if __name__ == "__main__":
    app.run(debug=True)