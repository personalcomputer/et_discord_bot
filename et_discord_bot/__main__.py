import asyncio
import logging

from .bot import ETBot
from .config import config


async def terminate_loop_if_unhealthy(loop, health_check):
    while health_check():
        await asyncio.sleep(1)
    logging.error("Unhealthy! Stopping asyncio loop.")
    loop.stop()


def main():
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%FT%TZ',
        level=logging.INFO
    )
    loop = asyncio.get_event_loop()

    try:
        bot = ETBot(config.discord_api_auth_token, loop)
        loop.create_task(bot.start())
        loop.create_task(terminate_loop_if_unhealthy(loop, lambda: bot.is_healthy()))
        loop.run_forever()
    except KeyboardInterrupt:
        logout_task = loop.create_task(bot.logout())
        loop.run_until_complete(logout_task)
    finally:
        loop.close()


if __name__ == '__main__':
    main()
