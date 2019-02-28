import requests
from sqlalchemy import create_engine
from datetime import datetime

conn_string = 'mysql://{user}:{password}@{host}/'.format(
                host = '35.237.252.223',
                user = 'root',
                password = 'x3rGjkz93e6CIkd7')
engine = create_engine(conn_string)
con = engine.connect()

engine.execute("CREATE DATABASE IF NOT EXISTS kayak")

sql = '''
CREATE TABLE IF NOT EXISTS kayak.flight (
    Airline varchar(70), 
    Price int(10),
    Date varchar(100),
    Time varchar(15),
    Timestamp datetime,
    Destination varchar(50),
    Prediction varchar(300)
)
'''

engine.execute(sql)


query_template = '''
INSERT IGNORE INTO kayak.flight(
    Airline, Price,
    Date, Time,
    Timestamp, Destination,
    Prediction)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
)
'''

