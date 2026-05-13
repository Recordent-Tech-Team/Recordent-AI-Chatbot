import os
from loguru import logger

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger.remove()
LOG_FORMAT = (
    "[{time:YYYY-MM-DDTHH:mm:ss.SSS}] "
    "[{level}] "
    "{extra[module]} - {message}"
)


# APP LOGS
logger.add(
    f"{LOG_DIR}/app.log",
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    format=LOG_FORMAT,
    filter=lambda record:
        record["extra"].get("module") != "access"
)

# ERROR LOGS
logger.add(
    f"{LOG_DIR}/error.log",
    level="ERROR",
    rotation="00:00",
    retention="7 days",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    format=LOG_FORMAT,
    filter=lambda record:
        record["extra"].get("module") != "access"
)

# ACCESS LOGS
logger.add(
    f"{LOG_DIR}/access.log",
    level="INFO",
    rotation="00:00",
    retention="7 days",
    enqueue=True,
    format=LOG_FORMAT,
    filter=lambda record:
        record["extra"].get("module") == "access"
)

def get_logger(module_name: str):
    return logger.bind(module=module_name)