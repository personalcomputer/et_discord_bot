import asyncio
import logging

from .globals import config
from .bot import ETBot


def main():
    logging.basicConfig(format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%FT%TZ', level=logging.INFO)
    loop = asyncio.get_event_loop()

    bot = ETBot(config.discord_api_auth_token, loop)
    loop.create_task(bot.start())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logout_task = loop.create_task(bot.logout())
        loop.run_until_complete(logout_task)
    finally:
        loop.close()


if __name__ == '__main__':
    main()
