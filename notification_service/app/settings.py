from starlette.config import Config

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

FROM_EMAIL = config("FROM_EMAIL", cast=str)
FROM_EMAIL_APP_PASSWORD = config("FROM_EMAIL_APP_PASSWORD", cast=str)
# TO_EMAIL = config("TO_EMAIL", cast=str)
# EMAIL_SUBJECT = config("EMAIL_SUBJECT", cast=str)


BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)

# KAFKA_TOPIC = config("KAFKA_TOPIC", cast=str)
# KAFKA_CONSUMER_GROUP_ID_FOR_USER = config("KAFKA_CONSUMER_GROUP_ID_FOR_USER", cast=str)

KAFKA_TOPIC_TO_CONSUME_NEW_USER = config("KAFKA_TOPIC_TO_CONSUME_NEW_USER", cast=str)
KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER = config("KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER", cast=str)

