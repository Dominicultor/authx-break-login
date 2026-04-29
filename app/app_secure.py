from flask import Flask, render_template, request, redirect, session
import sqlite3
import bcrypt
import time
import secrets

app = Flask(__name__)
app.secret_key = "super_secret_key_very_long_random_12345"

DB_NAME = "database_secure.db"

login_attempts = {}
MAX_ATTEMPTS = 3
LOCK_TIME = 60

reset_tokens = {}

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 6:
            return "Password too short"

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, hashed_password)
            )
            conn.commit()

            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO audit_logs (user_id, action, resource) VALUES (?, ?, ?)",
                (user_id, "REGISTER", "auth")
            )
            conn.commit()

            return "User created successfully"
        except:
            return "User already exists"

    return render_template("register_secure.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        now = time.time()

        if email in login_attempts:
            attempts = login_attempts[email]["attempts"]
            last = login_attempts[email]["last"]

            if attempts >= MAX_ATTEMPTS and now - last < LOCK_TIME:
                return "Too many attempts. Try later."

            if now - last >= LOCK_TIME:
                login_attempts[email] = {"attempts": 0, "last": now}

        conn = get_db_connection()
        cursor = conn.cursor()

        user = cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
                session["user"] = user["email"]

                login_attempts.pop(email, None)

                cursor.execute(
                    "INSERT INTO audit_logs (user_id, action, resource) VALUES (?, ?, ?)",
                    (user["id"], "LOGIN_SUCCESS", "auth")
                )
                conn.commit()

                return redirect("/dashboard")

        if email not in login_attempts:
            login_attempts[email] = {"attempts": 1, "last": now}
        else:
            login_attempts[email]["attempts"] += 1
            login_attempts[email]["last"] = now

        return "Invalid credentials"

    return render_template("login_secure.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html", user=session["user"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        conn = get_db_connection()
        cursor = conn.cursor()

        user = cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user:
            token = secrets.token_urlsafe(16)

            reset_tokens[token] = {
                "user_id": user["id"],
                "expires": time.time() + 300
            }

            return f"Reset token: {token}"

        return "Invalid request"

    return render_template("forgot_password_secure.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        token = request.form["token"]
        new_password = request.form["new_password"]

        if token in reset_tokens:
            data = reset_tokens[token]

            if time.time() > data["expires"]:
                return "Token expired"

            user_id = data["user_id"]

            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hashed_password, user_id)
            )
            conn.commit()

            reset_tokens.pop(token)

            return "Password reset successful"

        return "Invalid token"

    return render_template("reset_password_secure.html")


@app.route("/tickets")
def tickets():
    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (session["user"],)
    ).fetchone()

    tickets = cursor.execute(
        "SELECT * FROM tickets WHERE owner_id = ?",
        (user["id"],)
    ).fetchall()

    return render_template("tickets.html", tickets=tickets)


@app.route("/create-ticket", methods=["GET", "POST"])
def create_ticket():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]

        conn = get_db_connection()
        cursor = conn.cursor()

        user = cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (session["user"],)
        ).fetchone()

        cursor.execute(
            "INSERT INTO tickets (title, description, owner_id) VALUES (?, ?, ?)",
            (title, description, user["id"])
        )
        conn.commit()

        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, resource) VALUES (?, ?, ?)",
            (user["id"], "CREATE_TICKET", "ticket")
        )
        conn.commit()

        return redirect("/tickets")

    return render_template("create_ticket.html")


if __name__ == "__main__":
    app.run(debug=True)
