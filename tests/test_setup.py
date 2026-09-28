import sys
import mysql.connector
import pandas as pd
import nltk


def test_python_version():
    assert sys.version_info >= (3, 11)


def test_packages():
    assert pd is not None
    assert nltk is not None


def test_mysql_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="real_estate"
    )
    conn.close()