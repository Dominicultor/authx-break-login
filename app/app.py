from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"  # slab (intenționat)

DB_NAME = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return redirect("/login")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # ❌ parola in clar
            cursor.execute(f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')")
            conn.commit()
            return "User created successfully"
        except:
            return "User already exists"

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        # ❌ SQL INJECTION
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        user = cursor.execute(query).fetchone()

        if user:
            session["user"] = user["username"]
            return redirect("/dashboard")
        else:
            # ❌ user enumeration
            user_check = cursor.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchone()
            if user_check:
                return "Wrong password"
            else:
                return "User does not exist"

    return render_template("login.html")



# ---------------- FORGOT PASSWORD - VULNERABLE ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form["username"]

        conn = get_db_connection()
        cursor = conn.cursor()

        user = cursor.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchone()

        if user:
            token = username + "123"

            cursor.execute(
                f"INSERT INTO password_resets (username, token, used) VALUES ('{username}', '{token}', 0)"
            )
            conn.commit()

            return f"Reset token generated: {token}"

        return "User does not exist"

    return render_template("forgot_password.html")


# ---------------- RESET PASSWORD - VULNERABLE ----------------
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        token = request.form["token"]
        new_password = request.form["new_password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        reset = cursor.execute(
            f"SELECT * FROM password_resets WHERE token = '{token}'"
        ).fetchone()

        if reset:
            username = reset["username"]

            cursor.execute(
                f"UPDATE users SET password = '{new_password}' WHERE username = '{username}'"
            )
            conn.commit()

            return "Password reset successfully"

        return "Invalid token"

    return render_template("reset_password.html")
# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html", user=session["user"])


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
