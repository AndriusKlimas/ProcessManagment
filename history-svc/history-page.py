from flask import Flask, render_template, request
import os
import time
import pymysql
from pymysql.cursors import DictCursor

app = Flask(__name__)

def get_connection():
    for _ in range(30):
        try:
            return pymysql.connect(
                host=os.getenv("MARIADB_HOST", "mariadb-max"),
                port=int(os.getenv("MARIADB_PORT", "3306")),
                user=os.getenv("MARIADB_USER", "history_app"),
                password=os.getenv("MARIADB_PASSWORD", "history-password"),
                database=os.getenv("MARIADB_DATABASE", "history"),
                cursorclass=DictCursor,
                autocommit=True,
            )
        except pymysql.MySQLError:
            time.sleep(2)
    raise RuntimeError("MariaDB is not available")


def initialize_database():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS plays (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                song_name VARCHAR(255) NOT NULL,
                played_at VARCHAR(64) NOT NULL
            )""")

#when history page is loaded run below code
@app.route('/history-page')
def history_page():
    """Display the listening history for the logged-in user"""
    # Get username from cookie
    username = request.cookies.get('userID')
    
    if not username:
        # No user logged in
        return render_template('history-page.html.j2', username=None, history=[])
    
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT song_name, played_at AS timestamp FROM plays WHERE username=%s ORDER BY id DESC LIMIT 100",
                (username,),
            )
            history = cursor.fetchall()
    
    return render_template('history-page.html.j2', username=username, history=history)

#gets it from song-player.py
@app.route('/log-play', methods=['POST'])
def log_play():
    """Log a song play to user's history"""
    data = request.json
    username = data.get('username')
    song_name = data.get('song_name')
    
    if username and song_name:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO plays (username, song_name, played_at) VALUES (%s, %s, %s)",
                    (username, song_name, data.get('timestamp', '')),
                )
                cursor.execute(
                    """DELETE FROM plays WHERE username=%s AND id NOT IN
                    (SELECT id FROM (SELECT id FROM plays WHERE username=%s ORDER BY id DESC LIMIT 100) recent)""",
                    (username, username),
                )
    
    return {'status': 'logged'}


if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', debug=True)
