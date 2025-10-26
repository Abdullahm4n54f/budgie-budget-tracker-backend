import mysql.connector
from mysql.connector import Error

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '@Abdullah537', # <-- Put your password here
    'database': 'budgie_db'
}

connection = None
try:
    connection = mysql.connector.connect(**db_config)
    print("\n>>> Connection via script SUCCESSFUL! <<<\n")
except Error as e:
    print(f"\n!!! Connection via script FAILED: {e} !!!\n")
finally:
    if connection and connection.is_connected():
        connection.close()
        print("Connection closed.")