from flask import Flask, render_template, request
import logging
import os
import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

#Route get-catalog, found in nav bar on all pages
@app.route('/get-catalog')
def get_catalog():
    """ Return the catalog as a web page """
    response = requests.get("http://catalog-svc:5000/get-catalog", timeout=5)
    catalog = response.json()
    logger.info("Fetched catalog with %d products, status %s", len(catalog['catalog']), response.status_code)
    # Get username from cookie
    username = request.cookies.get('userID')
    #render and return the template
    return render_template("shop-front.html.j2", products=catalog['catalog'].values(), username=username)

if __name__ == '__main__':
    logger.info("Starting shop front service")
    app.run(debug=True, host='0.0.0.0', port=5000)
    