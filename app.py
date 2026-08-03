from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from flask import Flask, render_template, request, redirect, session
import sqlite3
from collections import defaultdict
app = Flask(__name__)
app.secret_key = "finance_tracker_secret"

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
        username TEXT UNIQUE,
        password TEXT
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
    status TEXT
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

            return "Username already exists!"

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
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Search
    search_query = request.args.get("search", "")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    if search_query:
        cursor.execute("""
            SELECT *
            FROM transactions
            WHERE user_id=? AND category LIKE ?
            ORDER BY id DESCquery = "SELECT * FROM transactions WHERE user_id=?"
params = [session["user_id"]]

if search_query:
    query += " AND category LIKE ?"
    params.append(f"%{search_query}%")

if from_date:
    query += " AND date >= ?"
    params.append(from_date)

if to_date:
    query += " AND date <= ?"
    params.append(to_date)

query += " ORDER BY id DESC"

cursor.execute(query, params)
        """, (session["user_id"], f"%{search_query}%"))
    else:
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
    monthly_values=list(monthly_data.values()),
    search_query=search_query,
    from_date=from_date,
    to_date=to_date
)
# ---------------- ADD TRANSACTION ---------------- #

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
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_transaction(id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("""
            UPDATE transactions
            SET date=?,
                type=?,
                category=?,
                amount=?,
                payment_method=?,
                description=?,
                status=?
            WHERE id=? AND user_id=?
        """, (
            request.form["date"],
            request.form["type"],
            request.form["category"],
            float(request.form["amount"]),
            request.form["payment_method"],
            request.form["description"],
            request.form["status"],
            id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    cursor.execute(
        "SELECT * FROM transactions WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    transaction = cursor.fetchone()

    conn.close()

    return render_template("edit.html", transaction=transaction)
# ---------------- DELETE TRANSACTION ---------------- #

@app.route("/delete/<int:id>")
def delete_transaction(id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM transactions WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")
@app.route("/download_pdf")
def download_pdf():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, type, category, amount
        FROM transactions
        WHERE user_id=?
        ORDER BY date DESC
    """, (session["user_id"],))

    transactions = cursor.fetchall()

    pdf_file = "finance_report.pdf"

    doc = SimpleDocTemplate(pdf_file)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("Personal Finance Tracker", styles["Title"]))
    elements.append(Paragraph(f"User: {session['username']}", styles["Heading2"]))

    data = [["Date", "Type", "Category", "Amount"]]

    for row in transactions:
        data.append([
            row["date"],
            row["type"],
            row["category"],
            str(row["amount"])
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))

    elements.append(table)

    doc.build(elements)

    conn.close()

    return send_file(pdf_file, as_attachment=True)

# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ---------------- RUN APPLICATION ---------------- #

if __name__ == "__main__":
    app.run(debug=True)