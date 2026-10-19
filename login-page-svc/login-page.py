from flask import Flask, render_template, request, redirect, session, make_response
import hashlib
import logging
import redis
import os
from redis.sentinel import Sentinel

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

sentinel = Sentinel(
    [
        (
            os.getenv("REDIS_SENTINEL_HOST", "redis"),
            int(os.getenv("REDIS_SENTINEL_PORT", "26379")),
        )
    ],
    socket_timeout=0.5,
)

r = sentinel.master_for(
    os.getenv("REDIS_MASTER_NAME", "mymaster"),
    db=int(os.getenv("REDIS_DB", "1")),
    decode_responses=True,
)


# # Connect to Redis for user storage
# r = redis.Redis(host='login-db', port=6379, decode_responses=True)


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
    
    stored_password = r.get(f'user:{username}')
    
    if stored_password is None:
        # User doesn't exist
        logger.info("Login failed: user %s does not exist", username)
        return render_template('login-page.html.j2', error='User does not exist. Please sign up first.')
    
    # Verify password
    if stored_password == hash_password(password):
        # Login successful - store in session and set cookie
        #session['username'] = username
        resp = make_response(redirect('/get-catalog'))
        resp.set_cookie('userID', username, path='/', samesite='Lax')
        logger.info("Login successful for user %s", username)
        return resp
    else:
        logger.info("Login failed: invalid password for user %s", username)
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
        logger.info("Signup rejected: missing username or password")
        return render_template('login-page.html.j2', error='Username and password are required.')
    
    # Check if passwords match
    if password != confirm_password:
        logger.info("Signup rejected: passwords do not match for user %s", username)
        return render_template('login-page.html.j2', error='Passwords do not match.')
    
    # Check if user already exists
    if r.exists(f'user:{username}'):
        logger.info("Signup rejected: user %s already exists", username)
        return render_template('login-page.html.j2', error='Username already exists.')

    r.set(f'user:{username}', hash_password(password))
    logger.info("Created account for user %s", username)
    return render_template('login-page.html.j2', success='Account created successfully! You can now login.')

#when user logs out, found on all pages
@app.route('/logout')
def logout():
    """Handle user logout"""
    #session.pop('username', None)
    resp = make_response(redirect('/login-page'))
    resp.set_cookie('userID', '', path='/', expires=0, max_age=0)
    logger.info("User logged out")
    return resp


if __name__ == '__main__':
    logger.info("Starting login service")
    app.run(host='0.0.0.0', debug=True)
