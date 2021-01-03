import gettext
import logging
import sys
from collections import OrderedDict

from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

from insults import Insulter


class Announcer:
    def __init__(self, sender):
        self.angery_level = 0
        self.logger = logging.getLogger("dudo.announcer")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        self.modes_thresholds = OrderedDict()

        self.current_poll = None
        self.poll_index = 0

        self.modes_thresholds["soft"] = 1.0
        self.modes_thresholds["normal"] = 2.0
        self.modes_thresholds["chilean"] = 3.0
        self.modes_thresholds["trava"] = float("infinity")

        self.mode = "soft"

        self.insulter = Insulter("insults.json")
        self.insulter.load()

        # self.locale (?)
        self.announcement_buffer = []
        self.sender = sender

        self.english = gettext.translation('dudobot', localedir="translations", languages=["en"], fallback=True)
        self.spanish = gettext.translation('dudobot', localedir="translations", languages=["chilean"], fallback=True)

        self._ = self.english.gettext

    def update_mode(self):
        angery_level = self.angery_level

        for mode, threshold in self.modes_thresholds.items():
            angery_level -= threshold
            if angery_level < 0:
                if self.mode == mode:
                    return
                self.mode = mode
                if mode == "normal" or mode == "soft":
                    self._ = self.english.gettext
                else:
                    self._ = self.spanish.gettext
                return

    def announce(self, announcement):
        self.announcement_buffer.append(announcement)

    async def force_announce(self):
        if self.current_poll is not None:

            player, question, initial_bet = self.current_poll
            self.current_poll = None

            if len(self.announcement_buffer[:self.poll_index]) > 0:
                await self.sender.sendMessage("\n".join(self.announcement_buffer[:self.poll_index]))
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Yes', callback_data='yes'),
                 InlineKeyboardButton(text='No', callback_data='no')],
            ])

            await self.sender.sendMessage(
                self._("%s asks '%s', starting with %d %s.") %
                (player, question, initial_bet, self._("person") if initial_bet == 1 else self._("people")),
                reply_markup=keyboard)

            if len(self.announcement_buffer[self.poll_index:]) > 0:
                await self.sender.sendMessage("\n".join(self.announcement_buffer[self.poll_index:]))
            self.announcement_buffer = []

        elif len(self.announcement_buffer) > 0:
            announcement = "\n".join(self.announcement_buffer)
            self.logger.debug("Announcing '%s'" % " ".join(self.announcement_buffer))
            self.announcement_buffer = []
            await self.sender.sendMessage(announcement)

    def get_angery(self):
        self.logger.debug("Getting angery...")
        self.angery_level += 1.0
        self.update_mode()

    def calm_down(self):
        self.angery_level -= 0.5
        self.update_mode()

    def save_poll(self, player, question, initial_bet):
        self.current_poll = (player, question, initial_bet)
        self.poll_index = len(self.announcement_buffer)

    def announce_start(self, player):
        self.announce("%s started a new game! Join by using /join." % player)

    def announce_cancel(self, player):
        self.announce("Game was cancelled by %s." % player)

    def announce_timeout(self):
        self.announce(self._("Time's up!"))

    def announce_too_high_bet(self, n_players):
        self.announce(self._("%s You can't bet that high. There's only %d players!")
                      % (self.insulter.get_insult(self.mode), n_players))
        self.get_angery()

    def announce_too_low_bet(self, current_bet):
        self.announce(self._("%s You should bet at least %d. If you can't, maybe you should doubt or fit.")
                      % (self.insulter.get_insult(self.mode), current_bet))
        self.get_angery()

    def announce_invalid_question(self):
        self.announce(self._("That's not a valid question! Remember to include your bet after '##'"))
        self.get_angery()

    def announce_timeout_kick(self, player_name):
        self.announce(self._("%s has taken too long. Kicking...") % player_name)
        self.get_angery()

    def announce_votes_received(self, names):
        self.announce(self._("All votes received."))
        self.announce_players(names)

    def announce_nonvoter_removal(self):
        self.announce(self._("Ok, we're done here. Removing everyone who didn't vote."))

    def announce_players(self, names):
        self.announce(self._("Current players are: %s.") % names)

    def announce_questioner(self, name):
        self.announce(self._("%s, it's your turn to ask a question.") % name)

    def announce_join(self, name):
        self.announce(self._("%s joined!") % name)

    def announce_fled(self, name):
        self.announce(self._("%s fled!") % name)

    def announce_guesser(self, name, question, bet):
        self.announce(self._("%s, it's your turn to make a guess. Question is '%s'. Current bet is %d.")
                      % (name, question, bet))

    def announce_round_finished(self, winner, loser, voters):
        self.announce(
            "Round ended! %s won and %s lost. The following players answered 'yes': %s." % (winner, loser, voters))

    def announce_end_game_too_few_players(self):
        self.announce(self._("Ending game, not enough players :("))

