#from auth import mysql
from auth.db import get_connection

# def find_user_by_email(email):
#     cursor = mysql.connection.cursor()
#     cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
#     user = cursor.fetchone()
#     cursor.close()
#     return user


def find_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# def create_user(name, email, hashed_pw):
#     cursor = mysql.connection.cursor()
#     cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_pw))
#     mysql.connection.commit()
#     cursor.close()

def create_user(name, email, hashed_pw):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
        (name, email, hashed_pw)
    )
    conn.commit()
    cursor.close()
    conn.close()
