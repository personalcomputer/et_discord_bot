import asyncio
import logging
import signal
import traceback
import StringIO

from .bot import ETBot
from .config import config


def handle_loop_exception(loop, context):
    logging.error(f'Exception in loop caught: {context["message"]}')
    if exception in context:
        exception_details = StringIO()
        traceback.print_exception(context['exception'], file=exception_details)
    logging.warn('Terminating asyncio loop')
    loop.stop()


def handle_sigterm():
    logging.warn('SIGTERM caught, terminating asyncio loop')
    asyncio.get_event_loop().stop()


def main():
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%FT%TZ',
        level=logging.INFO
    )
    signal.signal(signal.SIGTERM, handle_sigterm)

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_loop_exception)

    bot = ETBot(config.discord_api_auth_token, loop=loop)
    loop.create_task(bot.start())
    try:
        loop.run_forever()
    except KeyboardInterrupt as exception:
        handle_loop_exception(loop, {'message': 'KeyboardInterrupt', 'exception': exception})
    logging.info('Logging out')
    logout_task = loop.create_task(bot.logout())
    loop.run_until_complete(logout_task)


if __name__ == '__main__':
    main()
