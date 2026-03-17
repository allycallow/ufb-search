import json
import sys

from loguru import logger


def json_sink(message):
    record = message.record

    log_dict = {
        "level": record["level"].name.lower(),
        "time": record["time"].isoformat(),
        "msg": record["message"],
        "name": record["name"],
        "file": f"{record['file'].name}:{record['line']}",
    }

    log_dict.update(record.get("extra", {}))

    sys.stdout.write(json.dumps(log_dict) + "\n")
    sys.stdout.flush()


logger.remove()

logger.add(json_sink)
