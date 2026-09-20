"""Run separately; transactions make multiple sweepers safe."""
import os
import time
import logging
from .database import make_engine, transaction
from .protocol import expire

def main():
    engine=make_engine(os.environ["DATABASE_URL"])
    while True:
        try:
            with transaction(engine) as s: expire(s)
        except Exception: logging.exception("Expiry sweep failed")
        time.sleep(5)

if __name__=="__main__":main()
