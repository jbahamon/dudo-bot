import logging
import sys

import telepot
from telepot.aio.helper import ChatHandler

from actions import *
from statemachine import DudoStateMachine

BOT_NAME = "@du2bot"


class DudoHandler(ChatHandler):
    def __init__(self, *args, **kwargs):
        super(DudoHandler, self).__init__(*args, **kwargs)

        self.logger = logging.getLogger("dudo.handler")
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.StreamHandler(sys.stdout)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

        self.context = None

        logger = self.logger

        async def on_close(e):
            logger.debug("Dying...")
            if self.context is not None and not self.context.dead:
                self.context.destroy()
                self.logger.removeHandler(self.handler)
                await self.sender.sendMessage("You've been silent for too long. See ya next time!")

        self.on_close = on_close

    async def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)

        if self.context is not None and self.context.dead:
            self.context = None

        if content_type != "text":
            return

        text = msg["text"]
        tokens = text.split()

        if len(tokens) == 0:
            return

        command = tokens[0].lower()
        if command.endswith(BOT_NAME):
            command = command[:-len(BOT_NAME)]

        player = msg["from"]["id"]
        player_name = msg["from"]["first_name"]

        if self.context is None:
            await self.no_game_command(command, text, player, player_name)
        else:
            with await self.context.timeout_lock:
                await self.handle_command(command, text, player, player_name)

        if self.context is not None and self.context.dead:
            self.context = None

    async def no_game_command(self, command, text, player, player_name):

        if command == "/startgame" and self.context is None:
            self.context = DudoStateMachine(self.sender)
            with await self.context.timeout_lock:
                self.context.announce_start(player_name)
                self.context.start()
                self.context.on_input(Join(player, player_name))
                await self.context.force_announce()
        elif command == "/help":
            await self.sender.sendMessage(
                "Available commands are:\n"
                "\t /startgame\n"
                "\t /endgame\n"
                "\t /join\n"
                "\t /flee\n"
                "\t /ask question ## n (n being the initial bet)\n"
                "\t /raise n (raise the bet to an integer n > 0)\n"
                "\t /calzo\n"
                "\t /dudo\n"
                "\t /help"
            )

    async def handle_command(self, command, text, player, player_name):

        current_input = None
        if command == "/join":
            current_input = Join(player, player_name)
        elif command == "/flee":
            current_input = Flee(player)
        elif command == "/ask":

            question, initial_bet = self.parse_question(text)
            current_input = MakeQuestion(player, question, initial_bet)

        elif command == "/raise":

            bet = self.parse_bet(text)
            if bet is not None:
                current_input = MakeBet(player, bet)
            else:
                self.context.get_angery()

        elif command == "/dudo":
            current_input = Doubt(player)
        elif command == "/calzo":
            current_input = Fit(player)
        elif command == "/endgame" and self.context is not None:
            if self.context.game_owner == player:
                self.context.announce_cancel(player_name)
                await self.context.force_announce()
                self.context.destroy()
                self.context = None
                return
        else:
            return

        if self.context is not None and current_input is not None:
            self.context.on_input(current_input)

        if self.context is not None:
            await self.context.force_announce()

    async def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')

        if self.context is not None:
            val_to_add = 1 if query_data == "yes" else 0

            with await self.context.timeout_lock:
                self.context.on_input(Answer(from_id, val_to_add))
                await self.context.force_announce()

    @staticmethod
    def parse_question(text):
        if len(text.split(" ", 1)) <= 1:
            return None, None

        text = text.split(" ", 1)[1]

        tokens = text.split("##", 1)

        if len(tokens) < 2:
            return None, None

        try:
            question = tokens[0]
            initial_bet = int(tokens[1])

            return question, initial_bet

        except ValueError:
            return None, None

    @staticmethod
    def parse_bet(text):
        try:
            text = text.split(" ", 1)[1]
            return int(text)
        except ValueError:
            return None
        except IndexError:
            return None
