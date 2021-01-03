import asyncio
import concurrent
import logging
import sys

from announcer import Announcer
from states import State

MIN_PLAYERS = 2
FINAL_GUESS_DOUBT = "doubt"
FINAL_GUESS_FIT = "fit"


class DudoStateMachine(Announcer):
    def __init__(self, sender):
        Announcer.__init__(self, sender)
        self.logger = logging.getLogger("dudo.statemachine")
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.StreamHandler(sys.stdout)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

        self.angery_level = 0

        self.loop = asyncio.get_event_loop()
        self.timeout_task = None
        self.timeout_lock = asyncio.Lock()

        self.answers = dict()
        self.players = list()
        self.player_names = dict()

        self.previous_guesser = None
        self.current_state = None
        self.current_question = None

        self.questioners = list()
        self.guessers = list()

        self.current_bet = 0

        self.final_guess = None
        self.final_player = None

        self.game_owner = None
        self.timer = None
        self.dead = False

    def announce_players(self, names=None):
        if names is None:
            names = ", ".join([self.player_names[p] for p in self.players])

        super().announce_players(names)

    def announce_votes_received(self, names=None):
        if names is None:
            names = ", ".join([self.player_names[p] for p in self.players])

        super().announce_votes_received(names)

    def start(self):
        self.current_state = State.waiting_for_players
        self.current_state.run(self)
        # self.force_announce()

    def on_input(self, new_input):
        if not self.dead:
            self.logger.debug("Input %s" % new_input.action)
            new_input.apply(self, self.current_state)

    def go_to(self, state):
        self.current_state = state
        self.current_state.run(self)

    def add_player(self, player, name):
        if player not in self.players:
            self.player_names[player] = name
            self.players.append(player)
            self.questioners.append(player)
            self.guessers.append(player)
            self.announce_join(name)

            if len(self.players) == 1:
                self.game_owner = player

    def remove_player(self, player, silent=False):
        if player not in self.players:
            return False

        if not silent:
            self.announce_fled(self.player_names[player])

        self.players.remove(player)
        self.guessers.remove(player)
        self.questioners.remove(player)

        return True

    def announce_questioner(self, name=None):
        if name is None:
            name = self.player_names[self.guessers[0]]
        super().announce_questioner(name)

    def choose_next_questioner(self):
        assert len(self.players) > 0
        self.questioners.append(self.questioners.pop(0))

    def announce_guesser(self, name=None, question=None, bet=None):
        if name is None:
            name = self.player_names[self.guessers[0]]

        if question is None:
            question = self.current_question

        if bet is None:
            bet = self.current_bet

        super().announce_guesser(name, question, bet)

    def choose_next_guesser(self):
        assert len(self.players) > 0

        self.previous_guesser = self.questioners[0] if self.previous_guesser is None else self.guessers[0]
        self.guessers.append(self.guessers.pop(0))

    def add_answer(self, player, answer):
        if player not in self.players:
            return

        self.answers[player] = answer

    def check_game_over(self, min_players=MIN_PLAYERS):
        if len(self.players) < min_players:
            self.announce_end_game_too_few_players()
            self.destroy()
            return True
        return False

    def fit(self, player):
        if player not in self.players:
            return
        self.final_player = player
        self.final_guess = FINAL_GUESS_FIT
        self.end_game()

    def doubt(self, player):
        if player not in self.players:
            return
        self.cancel_timeout()
        self.final_player = player
        self.final_guess = FINAL_GUESS_DOUBT
        self.end_game()

    def clear(self):
        self.answers = dict()
        self.players = list()
        self.current_question = None
        self.questioners = list()
        self.guessers = None
        self.previous_guesser = None
        self.current_bet = 0
        self.final_guess = None
        self.final_player = None

    def end_game(self):
        if self.final_guess is not None and \
                        self.final_player is not None:
            self.cancel_timeout()
        else:
            return

        correct_number = sum(self.answers.values())

        if self.final_guess == FINAL_GUESS_FIT:
            final_player_won = self.current_bet == correct_number
        elif self.final_guess == FINAL_GUESS_DOUBT:
            final_player_won = self.current_bet > correct_number
        else:
            return

        winner, loser = (self.player_names[self.final_player], self.player_names[self.previous_guesser]) \
            if final_player_won else (self.player_names[self.previous_guesser], self.player_names[self.final_player])

        self.announce_round_finished(winner,
                                     loser,
                                     ", ".join((self.player_names[player_id] for player_id in
                                                (player_id for player_id in self.players
                                                 if self.answers[player_id] == 1))))

    def make_poll(self, player, question, initial_bet):

        self.current_bet = initial_bet
        self.current_question = question

        self.save_poll(player, question, initial_bet)

    def set_timeout(self, time):
        if self.timeout_task is not None:
            self.cancel_timeout()

        async def f():
            try:
                await asyncio.sleep(time)
                with await self.timeout_lock:
                    self.timeout_task = None
                    await self.on_timeout()
            except asyncio.CancelledError:
                pass

        self.timeout_task = self.loop.create_task(f())

    async def on_timeout(self):
        self.current_state.on_timeout(self)
        await self.force_announce()

    def cancel_timeout(self):
        if self.timeout_task is not None:
            self.timeout_task.cancel()
            self.timeout_task = None

    def remove_nonvoters(self):
        prev_length = len(self.players)
        for player in self.players:
            if player not in self.answers:
                self.remove_player(player, silent=False)

        if len(self.players) < prev_length:
            self.get_angery()

    def destroy(self):
        self.cancel_timeout()
        self.logger.removeHandler(self.handler)
        self.dead = True
