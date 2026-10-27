"""Entry point: python -m pi_sentinel"""

import logging

from .bot import PiSentinel
from .config import Config


def main() -> None:
    config = Config.from_env()
    bot = PiSentinel(config)
    bot.run(config.discord_token, log_level=logging.INFO, root_logger=True)


if __name__ == "__main__":
    main()
