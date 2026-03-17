import requests
from app.utils.logger import logger
from os import getenv

BACKEND_API_ENDPOINT = getenv("BACKEND_API_ENDPOINT", "http://localhost:8000")
BACKEND_API_KEY = getenv("BACKEND_API_KEY", "XXX-XXX-XXX")


def get_item_details(id: str, type: str) -> dict:
    logger.info("Getting item details", extra={"item_id": id})

    endpoint = f"{BACKEND_API_ENDPOINT}/api/{type}/{id}/"

    logger.info("Making request to backend API", extra={"endpoint": endpoint})

    response = requests.get(
        endpoint,
        headers={"x-api-key": BACKEND_API_KEY},
    )

    data = response.json()

    print(data)

    if not response.ok:
        raise Exception(f"Failed to get item details for {id}")

    return data
