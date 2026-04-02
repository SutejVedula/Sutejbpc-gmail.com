from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# 🔹 DATABASE CONNECTION
def get_db():
    return sqlite3.connect("database.db")

# 🔹 CREATE TABLES
def create_tables():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        available INTEGER
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS issued(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        borrower TEXT,
        issue_date TEXT,
        return_date TEXT
    )
    ''')

    conn.commit()
    conn.close()

create_tables()

# 🔐 LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "adminkap" and password == "kap1234":
            session['user'] = username
            return redirect('/')
        else:
            return "❌ Invalid Login"

    return render_template('login.html')

# 🔓 LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

def is_logged_in():
    return 'user' in session

# 🏠 HOME
@app.route('/')
def index():
    if not is_logged_in():
        return redirect('/login')

    query = request.args.get('q')

    conn = get_db()

    if query:
        books = conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ?",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        books = conn.execute("SELECT * FROM books").fetchall()

    conn.close()
    return render_template('index.html', books=books)

# ➕ ADD BOOK
@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if not is_logged_in():
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']

        conn = get_db()
        conn.execute(
            "INSERT INTO books (title, author, available) VALUES (?, ?, 1)",
            (title, author)
        )
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('add.html')

# 📤 ISSUE BOOK
@app.route('/issue', methods=['GET', 'POST'])
def issue_book():
    if not is_logged_in():
        return redirect('/login')

    conn = get_db()

    if request.method == 'POST':
        book_id = request.form['book_id']
        borrower = request.form['borrower']

        conn.execute(
            "INSERT INTO issued (book_id, borrower, issue_date, return_date) VALUES (?, ?, ?, NULL)",
            (book_id, borrower, datetime.now().strftime("%Y-%m-%d"))
        )

        conn.execute(
            "UPDATE books SET available=0 WHERE id=?",
            (book_id,)
        )

        conn.commit()
        conn.close()

        return redirect('/')

    books = conn.execute("SELECT * FROM books WHERE available=1").fetchall()
    conn.close()

    return render_template('issue.html', books=books)

# 📥 RETURN BOOK + UI PAGE
@app.route('/return', methods=['GET', 'POST'])
def return_book():
    if not is_logged_in():
        return redirect('/login')

    conn = get_db()

    if request.method == 'POST':
        issue_id = request.form['issue_id']

        record = conn.execute(
            "SELECT books.title, issued.book_id, issued.issue_date FROM issued JOIN books ON books.id = issued.book_id WHERE issued.id=?",
            (issue_id,)
        ).fetchone()

        title = record[0]
        book_id = record[1]
        issue_date = datetime.strptime(record[2], "%Y-%m-%d")

        days = (datetime.now() - issue_date).days
        fine = (days - 7) * 5 if days > 7 else 0

        conn.execute(
            "UPDATE issued SET return_date=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%d"), issue_id)
        )

        conn.execute(
            "UPDATE books SET available=1 WHERE id=?",
            (book_id,)
        )

        conn.commit()
        conn.close()

        return render_template("return_result.html",
                               title=title,
                               days=days,
                               fine=fine)

    issued_books = conn.execute('''
    SELECT issued.id, books.title, issued.borrower, issued.issue_date
    FROM issued
    JOIN books ON books.id = issued.book_id
    WHERE issued.return_date IS NULL
    ''').fetchall()

    conn.close()

    return render_template('return.html', issued_books=issued_books)

# 📊 REPORT
@app.route('/report')
def report():
    if not is_logged_in():
        return redirect('/login')

    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    issued = conn.execute("SELECT COUNT(*) FROM books WHERE available=0").fetchone()[0]
    available = conn.execute("SELECT COUNT(*) FROM books WHERE available=1").fetchone()[0]

    raw = conn.execute('''
    SELECT books.title, books.author, issued.borrower, issued.issue_date
    FROM issued
    JOIN books ON books.id = issued.book_id
    WHERE issued.return_date IS NULL
    ''').fetchall()

    report_data = []

    for r in raw:
        issue_date = datetime.strptime(r[3], "%Y-%m-%d")
        days = (datetime.now() - issue_date).days

        fine = (days - 7) * 5 if days > 7 else 0

        report_data.append({
            "title": r[0],
            "author": r[1],
            "borrower": r[2],
            "issue_date": r[3],
            "days": days,
            "fine": fine
        })

    conn.close()

    return render_template(
        'report.html',
        total=total,
        issued=issued,
        available=available,
        overdue=report_data
    )

# ▶️ RUN
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)