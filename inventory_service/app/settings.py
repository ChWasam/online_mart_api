from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
KAFKA_TOPIC = config("KAFKA_TOPIC", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY = config("KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY", cast=str)

KAFKA_TOPIC_GET = config("KAFKA_TOPIC_GET", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY_GET = config("KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY_GET", cast=str)

