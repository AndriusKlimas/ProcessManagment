"""
Song Player Service
This Flask app plays individual songs from the catalog.
The audio_mp3 filename from Redis is used in the URL to identify which song to play.
Only displays ONE song at a time - the song list is shown on shop-front page.
"""

from flask import Flask, render_template, request
import logging
import os
import requests
from datetime import datetime

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# Audio files are served through the Kubernetes Ingress.
AUDIO_BASE_URL = "/audio/"


@app.route('/play-songs/<audio_filename>')
def play_song(audio_filename):
    """
    Play a single song based on the audio_mp3 filename in the URL.
    
    Example URL: /play-songs/Pharrell%20Williams%20-%20Freedom%20(Video).mp3
    
    How it works:
    1. Get the audio filename from the URL (e.g., "Pharrell Williams - Freedom (Video).mp3")
    2. Fetch all songs from the catalog service
    3. Find the song that matches this audio_mp3 filename
    4. Display only that one song with its audio player
    """
    # Fetch all songs from the catalog service (which reads from Redis)
    response = requests.get("http://catalog-svc:5000/get-catalog", timeout=5)
    catalog = response.json()
    
    # Search through all songs to find the one with matching audio_mp3 filename
    song_to_play = None
    for song in catalog['catalog'].values():
        if song.get('audio_mp3') == audio_filename:
            song_to_play = song
            break

    if song_to_play:
        logger.info("Found song %s for playback", song_to_play.get('name', 'Unknown'))
    else:
        logger.info("Song not found for playback request: %s", audio_filename)
    
    # Log the play to history if user is logged in
    username = request.cookies.get('userID')
    if username and song_to_play:
        try:
            requests.post("http://history:5000/log-play", 
                         json={
                             'username': username,
                             'song_name': song_to_play.get('name', 'Unknown'),
                             'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                         },
                         timeout=2)
            logger.info("Sent playback history for user %s", username)
        except requests.RequestException:
            logger.warning("Unable to send playback history for user %s", username)
    
    # Render the template with the single song (or None if not found)
    return render_template("song-player.html.j2", 
                           song=song_to_play, 
                           audio_base_url=AUDIO_BASE_URL,
                           audio_filename=audio_filename)


if __name__ == '__main__':
    logger.info("Starting song player service")
    app.run(debug=True, host='0.0.0.0', port=5000)
