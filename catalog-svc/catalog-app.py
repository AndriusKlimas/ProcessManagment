import json
import os
import time
from flask import Flask, request
import pymysql
from pymysql.cursors import DictCursor

app = Flask(__name__)


catalog = {"catalog": {
    "Apple-iPhone-14": {"make": "Apple", "model": "iPhone 14", "price": 699.99},
    "Samsung-Galaxy-S22": {"make": "Samsung", "model": "Galaxy S22", "price": 799.99},
    "Google-Pixel-6": {"make": "Google", "model": "Pixel 6", "price": 599.99},
    "apple-watch-8": {"make": "Apple", "model": "Watch 8", "price": 399.99}}
    }


def get_connection():
    for _ in range(30):
        try:
            return pymysql.connect(
                host=os.getenv("MARIADB_HOST", "mariadb-max"),
                port=int(os.getenv("MARIADB_PORT", "3306")),
                user=os.getenv("MARIADB_USER", "catalog_app"),
                password=os.getenv("MARIADB_PASSWORD", "catalog-password"),
                database=os.getenv("MARIADB_DATABASE", "catalog"),
                cursorclass=DictCursor,
                autocommit=True,
            )
        except pymysql.MySQLError:
            time.sleep(2)
    raise RuntimeError("MariaDB is not available")


def initialize_database():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS products (
                product_key VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                artist VARCHAR(255) NOT NULL,
                album VARCHAR(255) NOT NULL,
                audio_mp3 VARCHAR(255) NOT NULL,
                uploader VARCHAR(255) NOT NULL,
                make VARCHAR(255),
                model VARCHAR(255),
                price DECIMAL(10, 2)
            )""")
            cursor.execute("SELECT COUNT(*) AS count FROM products")
            if cursor.fetchone()["count"] == 0:
                for key, product in catalog["catalog"].items():
                    cursor.execute(
                        """INSERT INTO products
                        (product_key, name, artist, album, audio_mp3, uploader, make, model, price)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (key, product.get("model", key), product.get("make", ""), "", "", "system", product.get("make"), product.get("model"), product.get("price")),
                    )

#Route get catalog as JSON, called from shop-front-svc
@app.route('/get-catalog')
def get_catalog():
    """ Return the catalog as a JASON """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM products ORDER BY product_key")
            rows = cursor.fetchall()

    data = {}
    for row in rows:
        product_key = row.pop("product_key")
        if row.get("price") is not None:
            row["price"] = float(row["price"])
        data[product_key] = row

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

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO products
                (product_key, name, artist, album, audio_mp3, uploader)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name=VALUES(name), artist=VALUES(artist),
                album=VALUES(album), audio_mp3=VALUES(audio_mp3), uploader=VALUES(uploader)""",
                (key, product["name"], product["artist"], product["album"], product["audio_mp3"], product["uploader"]),
            )


    return{"Status": "Product added successfully"}


if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, host='0.0.0.0', port=5000)

