from flask import Flask, render_template, request, redirect, session, make_response
import hashlib
import os
import time
import pymysql
from pymysql.cursors import DictCursor

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

def get_connection():
    for _ in range(30):
        try:
            return pymysql.connect(
                host=os.getenv("MARIADB_HOST", "mariadb-max"),
                port=int(os.getenv("MARIADB_PORT", "3306")),
                user=os.getenv("MARIADB_USER", "login_app"),
                password=os.getenv("MARIADB_PASSWORD", "login-password"),
                database=os.getenv("MARIADB_DATABASE", "login"),
                cursorclass=DictCursor,
                autocommit=True,
            )
        except pymysql.MySQLError:
            time.sleep(2)
    raise RuntimeError("MariaDB is not available")


def initialize_database():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS users (username VARCHAR(255) PRIMARY KEY, password_hash CHAR(64) NOT NULL)")

#privating the password
def hash_password(password):
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

#when login page is loaded
@app.route('/login-page')
def login_page():
    """Display the login/signup page"""
    return render_template('login-page.html.j2')

#when login function is ran, in html file
@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
    stored_password = user["password_hash"] if user else None
    
    if stored_password is None:
        # User doesn't exist
        return render_template('login-page.html.j2', error='User does not exist. Please sign up first.')
    
    # Verify password
    if stored_password == hash_password(password):
        # Login successful - store in session and set cookie
        #session['username'] = username
        resp = make_response(redirect('/get-catalog'))
        resp.set_cookie('userID', username, path='/', samesite='Lax')
        return resp
    else:
        return render_template('login-page.html.j2', error='Invalid password.')

#when signup function is ran, in html file
@app.route('/signup', methods=['POST'])
def signup():
    """Handle user registration"""
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not username or not password:
        return render_template('login-page.html.j2', error='Username and password are required.')
    
    # Check if passwords match
    if password != confirm_password:
        return render_template('login-page.html.j2', error='Passwords do not match.')
    
    # Check if user already exists
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                return render_template('login-page.html.j2', error='Username already exists.')
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, hash_password(password)),
            )
    
    return render_template('login-page.html.j2', success='Account created successfully! You can now login.')

#when user logs out, found on all pages
@app.route('/logout')
def logout():
    """Handle user logout"""
    #session.pop('username', None)
    resp = make_response(redirect('/login-page'))
    resp.set_cookie('userID', '', path='/', expires=0, max_age=0)
    return resp


if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', debug=True)
