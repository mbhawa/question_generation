import os

from conf.documents import ParsedData, QueryData, UserData
from dotenv import load_dotenv
from mongoengine import connect

load_dotenv()


# Define your MongoDB connection parameters
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_PORT = os.getenv("MONGODB_PORT")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_DBNAME = os.getenv("MONGODB_DBNAME")
MONGODB_ALIAS = os.getenv("MONGODB_ALIAS")


MONGODB_CLOUD_HOST = os.getenv("MONGODB_CLOUD_HOST")
MONGODB_CLOUD_USERNAME = os.getenv("MONGODB_CLOUD_USERNAME")
MONGODB_CLOUD_PASSWORD = os.getenv("MONGODB_CLOUD_PASSWORD")

IS_MONGO_CLOUD = os.getenv("IS_MONGO_CLOUD","true").lower() in ('true', '1', 't', 'y', 'yes')

def connect_to_mongo():

    if IS_MONGO_CLOUD:
        host=f"mongodb+srv://{MONGODB_CLOUD_USERNAME}:{MONGODB_CLOUD_PASSWORD}@{MONGODB_CLOUD_HOST}"
        print("=-=-=-=", host)
    else:
        host=f"mongodb://localhost:27017/mydatabase",
        print("-=-=-=-=-", host)


    connect(
        db=MONGODB_DBNAME,
        host=host,
        alias="default",
    )


def create_database():
    UserData.objects().first()
    QueryData.objects().first()
    ParsedData.objects().first()
