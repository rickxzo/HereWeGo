import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

def connect_db():
    return psycopg2.connect(
        host="ep-floral-king-apuib0ib-pooler.c-7.us-east-1.aws.neon.tech",
        dbname="neondb",
        user="neondb_owner",
        password=os.getenv('NEONDB_PASS2'),
        sslmode="require",
    )
