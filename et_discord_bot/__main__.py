import logging
import signal
import asyncio

from .bot import ETBot
from .config import config


async def terminate_loop_if_bot_unhealthy(loop, bot):
    while bot.is_healthy():
        await asyncio.sleep(1)
    logging.error("Unhealthy! Stopping asyncio loop.")
    loop.stop()


async def gracefully_terminate(loop, bot):
    await bot.logout()
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
        loop.create_task(terminate_loop_if_bot_unhealthy(loop, bot))
        loop.add_signal_handler(signal.SIGINT, lambda: loop.create_task(gracefully_terminate(loop, bot)))
        loop.add_signal_handler(signal.SIGTERM, lambda: loop.create_task(gracefully_terminate(loop, bot)))
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    main()
