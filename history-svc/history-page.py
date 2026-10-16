from flask import Flask, render_template, request
import redis
import json

app = Flask(__name__)

# Connect to Redis for history storage
r = redis.Redis(host='catalog-db', port=6379, decode_responses=True)


#when history page is loaded run below code
@app.route('/history-page')
def history_page():
    """Display the listening history for the logged-in user"""
    # Get username from cookie
    username = request.cookies.get('userID')
    
    if not username:
        # No user logged in
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
    
    return {'status': 'logged'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
