import psycopg2
import os


def db_connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def fetch_one_as_dict(query: str, params: tuple = None):
    conn = db_connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                columns = [desc[0].lower() for desc in cursor.description]

                row = cursor.fetchone()
                if row:
                    return dict(zip(columns, row))
    finally:
        conn.close()
    return None


def fetch_all_as_dict(query: str, params: tuple = None):
    conn = db_connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                columns = [desc[0].lower() for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()
    return []
