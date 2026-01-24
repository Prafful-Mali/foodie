import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Hello from foodie!")


if __name__ == "__main__":
    main()
