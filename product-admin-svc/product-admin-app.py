from flask import Flask, redirect, render_template, request
import logging
import os
import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)
#route add product, when user loads the add-product-page
@app.route('/add-product-page')
def add_product_page():
    """ Return the add product page """
    logger.info("Product creation page requested")
    return render_template("add-product.html.j2")

#route add-product, called from add-product-page.html.j2
@app.route('/add-product', methods=['POST'])
def add_product():
    if request.method == 'POST': 
        f = request.files['audio_mp3']
        f.save("/root/app/song-locations/" + f.filename)
    """ Add product to catalog service """
    # Get uploader from cookie
    uploader = request.cookies.get('userID', 'Unknown')
    
    product = {
        "name": request.form['name'],
        "artist": request.form['artist'],
        "album": request.form['album'],
        "audio_mp3": f.filename,
        "uploader": uploader
    }
    response = requests.post("http://catalog-svc:5000/add-product", json=product, timeout=5)
    logger.info("Submitted product %s to catalog service with status %s", product["name"], response.status_code)

    return redirect("/get-catalog")

if __name__ == '__main__':
    logger.info("Starting product admin service")
    app.run(debug=True, host='0.0.0.0', port=5000)