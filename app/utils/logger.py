import json
import sys
from os import getenv

from logtail import LogtailHandler
from loguru import logger

BETTER_STACK_TOKEN = getenv("BETTER_STACK_TOKEN")

handler = LogtailHandler(
    source_token=BETTER_STACK_TOKEN,
    host="https://s2303099.eu-fsn-3.betterstackdata.com",
)


def json_sink(message):
    record = message.record

    log_dict = {
        "level": record["level"].name.lower(),
        "time": record["time"].isoformat(),
        "msg": record["message"].strip(),  # <-- changed from "formatted" to "message"
        "name": record["name"],
        "file": f"{record['file'].name}:{record['line']}",
    }

    extra = record.get("extra", {})
    if "extra" in extra and isinstance(extra["extra"], dict):
        extra = {**extra, **extra.pop("extra")}

    log_dict.update(extra)

    sys.stdout.write(json.dumps(log_dict) + "\n")
    sys.stdout.flush()


logger.remove()

logger.add(
    sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss} | {level} | {message} | {extra}"
)

logger.add(json_sink)

logger.add(handler, format="{message}", backtrace=False, diagnose=False)
