from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

# JWT VARIABLES
SECRET_KEY = config("SECRET_KEY", cast=str)
ALGORITHM = config("ALGORITHM", cast=str)
JWT_EXPIRY_TIME = config("JWT_EXPIRY_TIME", cast=int)


DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
KAFKA_TOPIC = config("KAFKA_TOPIC", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_USER = config("KAFKA_CONSUMER_GROUP_ID_FOR_USER", cast=str)

KAFKA_TOPIC_GET = config("KAFKA_TOPIC_GET", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_USER_GET = config("KAFKA_CONSUMER_GROUP_ID_FOR_USER_GET", cast=str)


KAFKA_TOPIC_STOCK_LEVEL_CHECK = config("KAFKA_TOPIC_STOCK_LEVEL_CHECK", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_STOCK_LEVEL_CHECK = config("KAFKA_CONSUMER_GROUP_ID_FOR_STOCK_LEVEL_CHECK", cast=str)


KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER = config("KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER", cast=str)
KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT = config("KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT", cast=str)