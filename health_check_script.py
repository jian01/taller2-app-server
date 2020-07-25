import requests
import os
import time

DEFAULT_SLEEP_TIME = 1
DEFAULT_TIMEOUT = 30

r = None
while not r or r.status_code != 200:
    time.sleep(DEFAULT_SLEEP_TIME)
    try:
        r = requests.get("http://localhost:%s/health" % os.getenv("PORT"), timeout=DEFAULT_TIMEOUT)
    except TimeoutError:
        print("Health check: Timeout for healthy check")
    except requests.exceptions.ConnectionError:
        print("Health check: Connection error")
print("Health check ended")