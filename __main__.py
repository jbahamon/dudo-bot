import asyncio
import sys

import telepot
from telepot.aio.delegate import pave_event_space, per_chat_id, create_open, include_callback_query_chat_id
from telepot.aio.loop import MessageLoop

from handler import DudoHandler

TOKEN = ""


def main(args=None):
    """The main routine"""
    if args is None:
        args = sys.argv[1:]

    bot = telepot.aio.DelegatorBot(TOKEN, [
        include_callback_query_chat_id(pave_event_space())(
            per_chat_id(types=["group"]), create_open, DudoHandler, timeout=300),
    ])

    loop = asyncio.get_event_loop()
    loop.create_task(MessageLoop(bot).run_forever())
    loop.run_forever()


if __name__ == "__main__":
    main()
