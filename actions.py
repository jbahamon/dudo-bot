class PlayerAction:
    def __init__(self, action, player=None):
        self.player = player
        self.action = action

    def __str__(self): return "%s: %s" % (self.player, self.action)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def apply(self, context, state):
        raise NotImplementedError("not implemented")


class Join(PlayerAction):
    def __init__(self, player, name):
        PlayerAction.__init__(self, "Join", player)
        self.name = name

    def apply(self, context, state):
        state.on_join(context, self.player, self.name)


class Flee(PlayerAction):
    def __init__(self, player):
        PlayerAction.__init__(self, "Flee", player)

    def apply(self, context, state):
        state.on_flee(context, self.player)


class MakeQuestion(PlayerAction):
    def __init__(self, player, question, initial_bet):
        PlayerAction.__init__(self, "MakeQuestion", player)
        self.question = question
        self.initial_bet = initial_bet

    def apply(self, context, state):
        state.on_question(context, self.player, self.question, self.initial_bet)


class Answer(PlayerAction):
    def __init__(self, player, answer):
        PlayerAction.__init__(self, "Answer", player)
        self.answer = answer

    def apply(self, context, state):
        state.on_answer(context, self.player, self.answer)


class MakeBet(PlayerAction):
    def __init__(self, player, bet):
        PlayerAction.__init__(self, "MakeBet", player)
        self.bet = bet

    def apply(self, context, state):
        state.on_bet(context, self.player, self.bet)


class Doubt(PlayerAction):
    def __init__(self, player):
        PlayerAction.__init__(self, "Doubt", player)

    def apply(self, context, state):
        state.on_doubt(context, self.player)


class Fit(PlayerAction):
    def __init__(self, player):
        PlayerAction.__init__(self, "Fit", player)

    def apply(self, context, state):
        state.on_fit(context, self.player)


class End(PlayerAction):
    def __init__(self, player):
        PlayerAction.__init__(self, "End", player)

    def apply(self, context, state):
        state.on_destroy(context, self.player)
