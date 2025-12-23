# pizza.py
import asyncio
import logging
import json
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')

logging.basicConfig(level=logging.INFO)

MENU = [
    {"name": "Pepperoni"},
    {"name": "Margherita"},
    {"name": "Vegetarian"},
    {"name": "Hawaiian"},
    {"name": "Meat Lovers"},
    {"name": "BBQ Chicken"},
    {"name": "Supreme"},
    {"name": "Four Cheese"}
]

def save_order_to_db(orderdict: dict):
    required_keys = {'qty', 'product', 'ptype'}
    if not required_keys.issubset(orderdict):
        raise ValueError("Missing required keys")

    cnx = mysql.connector.connect(
        user='root',
        password=DB_PASSWORD,
        host='127.0.0.1',
        database='mybot'
    )
    query = """
        INSERT INTO orders (product, ptype, qty)
        SELECT product, ptype, qty FROM
        JSON_TABLE(%s, "$" COLUMNS(
            qty INT PATH '$.qty',
            product VARCHAR(30) PATH "$.product",
            ptype VARCHAR(30) PATH "$.ptype"
        )) AS jt1
    """
    cursor = cnx.cursor()
    cursor.execute(query, (json.dumps(orderdict),))
    cnx.commit()
    cursor.close()
    cnx.close()