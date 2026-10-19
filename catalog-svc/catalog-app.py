import json
import logging
from flask import Flask, request
import redis
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
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True,
)
# r = redis.Redis(host="catalog-db", port=6379, decode_responses=True)


catalog = {"catalog": {
    "Apple-iPhone-14": {"make": "Apple", "model": "iPhone 14", "price": 699.99},
    "Samsung-Galaxy-S22": {"make": "Samsung", "model": "Galaxy S22", "price": 799.99},
    "Google-Pixel-6": {"make": "Google", "model": "Pixel 6", "price": 599.99},
    "apple-watch-8": {"make": "Apple", "model": "Watch 8", "price": 399.99}}
    }

#Route get catalog as JSON, called from shop-front-svc
@app.route('/get-catalog')
def get_catalog():
    """ Return the catalog as a JASON """
    data = r.hgetall("catalog")
    logger.info("Loaded %d products from catalog", len(data))

    for key in data.keys():
        data[key] = json.loads(data[key])

    return {"catalog": data}


#route to add new products to catalog, called from product-admin-svc
@app.route('/add-product', methods=['POST'])
def add_product():
    """add new product to catalog"""
    product = {
        "name": request.json['name'],
        "artist": request.json['artist'],
        "album": request.json['album'],
        "audio_mp3": request.json['audio_mp3'],
        "uploader": request.json.get('uploader', 'Unknown')
    }
    



    #Create a nutral key for make and product
    key = request.json['name'] + "-" + request.json['artist']

    r.hset("catalog", key=key, value=json.dumps(product))
    logger.info("Added product %s to catalog", key)


    return{"Status": "Product added successfully"}


if __name__ == '__main__':
    logger.info("Starting catalog service")
    app.run(debug=True, host='0.0.0.0', port=5000)

