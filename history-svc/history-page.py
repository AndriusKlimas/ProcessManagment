from flask import Flask, render_template, request
import redis
import logging
import json
import os
from redis.sentinel import Sentinel

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

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
    db=int(os.getenv("REDIS_DB", "2")),
    decode_responses=True,
    socket_timeout=0.5,
    socket_connect_timeout=0.5,
)

# # Connect to Redis for history storage
# r = redis.Redis(host='catalog-db', port=6379, decode_responses=True)


#when history page is loaded run below code
@app.route('/history-page')
def history_page():
    """Display the listening history for the logged-in user"""
    # Get username from cookie
    username = request.cookies.get('userID')
    
    if not username:
        # No user logged in
        logger.info("History requested without an authenticated user")
        return render_template('history-page.html.j2', username=None, history=[])
    
    history_key = f'history:{username}'
    history_data = r.lrange(history_key, 0, -1)

    history = []
    for item in history_data:
        try:
            history.append(json.loads(item))
        except Exception:
            pass

    history.reverse()
    logger.info("Loaded %d history entries for user %s", len(history), username)
    
    return render_template('history-page.html.j2', username=username, history=history)

#gets it from song-player.py
@app.route('/log-play', methods=['POST'])
def log_play():
    """Log a song play to user's history"""
    data = request.json
    username = data.get('username')
    song_name = data.get('song_name')
    
    if username and song_name:
        history_key = f'history:{username}'
        history_entry = json.dumps({
            'song_name': song_name,
            'timestamp': data.get('timestamp', '')
        })
        r.rpush(history_key, history_entry)
        r.ltrim(history_key, -100, -1)
        logger.info("Recorded play for user %s", username)
    else:
        logger.info("Ignored play request with missing user or song")
    
    return {'status': 'logged'}


if __name__ == '__main__':
    logger.info("Starting history service")
    app.run(host='0.0.0.0', debug=True)
