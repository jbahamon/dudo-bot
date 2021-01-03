class State:
    def __init__(self):
        pass

    def run(self, context):
        pass

    # Default empty implementations

    def on_join(self, context, player, name):
        pass

    def on_flee(self, context, player):
        pass

    def on_timeout(self, context):
        return

    def on_question(self, context, player, question, initial_bet):
        pass

    def on_answer(self, context, player, answer):
        pass

    def on_bet(self, context, player, bet):
        pass

    def on_doubt(self, context, player):
        pass

    def on_fit(self, context, player):
        pass


class WaitingForPlayers(State):
    def run(self, context):
        context.set_timeout(60)

    def on_join(self, context, player, name):
        context.add_player(player, name)
        context.set_timeout(30)

    def on_flee(self, context, player):
        context.remove_player(player)
        context.set_timeout(30)
        context.check_game_over(1)

    def on_timeout(self, context):
        context.announce_timeout()
        if context.check_game_over():
            return
        context.go_to(State.waiting_for_question)


class WaitingForQuestion(State):
    def run(self, context):
        context.announce_questioner()
        context.set_timeout(50)

    def on_flee(self, context, player):
        was_questioner = player == context.questioners[0]
        context.logger.debug("Was questioner: %r" % was_questioner)
        context.remove_player(player)
        if not context.check_game_over() and was_questioner:
            context.go_to(State.waiting_for_question)

    def on_question(self, context, player, question, initial_bet):
        if player == context.questioners[0]:
            if initial_bet is not None and initial_bet > len(context.players):
                context.announce_too_high_bet(len(context.players))
                context.set_timeout(50)
                return

            if question is not None and initial_bet is not None:
                context.question = question
                context.make_poll(context.player_names[player], question, initial_bet)
                context.choose_next_guesser()
                context.go_to(State.waiting_for_answers)
            else:
                context.announce_invalid_question()
                context.set_timeout(50)

    def on_timeout(self, context):
        context.announce_timeout_kick(context.player_names[context.questioners[0]])
        context.remove_player(context.questioners[0], silent=True)
        if not context.check_game_over():
            context.go_to(State.waiting_for_question)


class WaitingForAnswers(State):
    def run(self, context):
        context.set_timeout(50)

    def on_flee(self, context, player):
        context.remove_player(player)
        context.check_game_over()

    def on_answer(self, context, player, answer):
        context.add_answer(player, answer)

        for player in context.players:
            if player not in context.answers:
                return

        context.announce_votes_received()
        context.go_to(State.waiting_for_guess)

    def on_timeout(self, context):
        context.announce_nonvoter_removal()
        context.remove_nonvoters()

        if not context.check_game_over():
            context.announce_players()
            context.go_to(State.waiting_for_guess)


class WaitingForGuess(State):
    def run(self, context):
        context.announce_guesser()
        context.set_timeout(50)

    def on_flee(self, context, player):
        was_guesser = player == context.guessers[0]
        context.logger.debug("Was guesser: %r" % was_guesser)
        context.remove_player(player)
        if not context.check_game_over() and was_guesser:
            context.go_to(State.waiting_for_guess)

    def on_bet(self, context, player, bet):
        if player != context.guessers[0]:
            return

        if bet > len(context.players):
            context.announce_too_high_bet(len(context.players))
            context.set_timeout(50)
            return

        if bet <= context.current_bet:
            context.announce_too_low_bet(context.current_bet)
            context.set_timeout(50)
            return

        context.current_bet = bet
        context.choose_next_guesser()
        context.go_to(State.waiting_for_guess)

    def on_doubt(self, context, player):
        if context.guessers[0] != player or context.previous_guesser is None:
            return
        context.doubt(player)
        context.go_to(State.waiting_for_question)

    def on_fit(self, context, player):
        if context.guessers[0] != player or context.previous_guesser is None:
            return
        context.fit(player)
        context.go_to(State.waiting_for_question)

    def on_timeout(self, context):
        context.announce_timeout_kick(context.player_names[context.guessers[0]])
        context.remove_player(context.guessers[0], silent=True)

        if not context.check_game_over():
            context.go_to(State.waiting_for_guess)


State.waiting_for_players = WaitingForPlayers()
State.waiting_for_question = WaitingForQuestion()
State.waiting_for_guess = WaitingForGuess()
State.waiting_for_answers = WaitingForAnswers()
