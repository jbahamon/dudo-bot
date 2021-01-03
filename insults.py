# coding=utf-8
import json
import random
import re
from collections import defaultdict


class Insulter:
    def __init__(self, file_name):
        self.file_obj = open(file_name, encoding="utf8")
        self.insult_cfgs = dict()

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file_obj.close()
        return True

    def modes(self):
        return list(self.insult_cfgs.keys())

    def load(self):
        insults = json.loads(self.file_obj.read())

        soft_cfg = CFG()
        # soft insults
        soft_cfg.add_prod("S", "INTRO INSULT")
        soft_cfg.add_prod("INTRO", "Oh, you | You")
        soft_cfg.add_prod("INSULT", "ADJ SIMPLE_NOUN | NOUN")

        soft_cfg.add_prod("NOUN", " | ".join(insults["soft_nouns"]))
        soft_cfg.add_prod("SIMPLE_NOUN", " | ".join(insults["soft_simple_nouns"]))
        soft_cfg.add_prod("ADJ", " | ".join(insults["soft_adjectives"]))

        # shakespearean insult
        shakespeare_cfg = CFG()
        shakespeare_cfg.add_prod("S", "INTRO ADJ1 , ADJ2 NOUN END")
        shakespeare_cfg.add_prod("INTRO", "Oh, you | You")

        shakespeare_cfg.add_prod("ADJ1", " | ".join(insults["old_adjectives_one"]))
        shakespeare_cfg.add_prod("ADJ2", " | ".join(insults["old_adjectives_two"]))
        shakespeare_cfg.add_prod("NOUN", " | ".join(insults["old_nouns"]))
        shakespeare_cfg.add_prod("END", ". | !")

        # pythonic insult
        python_cfg = CFG()
        python_cfg.add_prod("S", "EXCLAMATION | INSULT END")
        python_cfg.add_prod("INSULT", "INTRO _2ADJECTIVE NOUN")

        python_cfg.bind("2ADJECTIVE", lambda: ", ".join(random.sample(insults["adjectives"], 2)))

        python_cfg.add_prod("INTRO", "Oh, you | You")

        python_cfg.add_prod("EXCLAMATION",
                            "I ACTION , you ADJECTIVE NOUN END | ORDER , you ADJECTIVE NOUN END")
        python_cfg.add_prod("ORDER", "Go and boil your bottoms | Cut your prancing or I shall taunt you a second time")
        python_cfg.add_prod("ACTION",
                            "blow my nose at you | fart in your general direction | burst my pimples at you | "
                            "unclog my nose in your direction | wave my private parts at your aunties")

        python_cfg.add_prod("ADJECTIVE", " | ".join(insults["python_adjectives"]))
        python_cfg.add_prod("NOUN", " | ".join(insults["python_nouns"]))

        python_cfg.add_prod("END", ". | !")

        # generic insults
        normal_cfg = CFG()
        normal_cfg.add_prod("S", "INTRO ADJ NOUN END| INTRO NOUN END")
        normal_cfg.add_prod("INTRO", "You | What a | You're such a ")
        normal_cfg.add_prod("ADJ", "ADJ , ADJ | %s" % " | ".join(insults["adjectives"]))
        normal_cfg.add_prod("NOUN", " | ".join(insults["nouns"]))
        normal_cfg.add_prod("END", ". | !")

        trava_cfg = CFG()
        trava_cfg.add_prod("S", " | ".join(insults["trava_insults"]))

        # chilean!
        chilean_cfg = CFG()
        chilean_cfg.add_prod("S",
                             "Si seguís con eso, podís irte a la PLACE , INSULT . | "
                             "Este NOUN no es más ADJECTIVE porque no se levanta más temprano .| "
                             "Puta que es ADJECTIVE este NOUN .")

        chilean_cfg.add_prod("INSULT", "ADJECTIVE NOUN .")
        chilean_cfg.add_prod("ADJECTIVE", "culiao | reculiao | enfermo | imbécil")
        chilean_cfg.add_prod("NOUN", "aweonao | weón | engendro | sapo | hijo de WHORE | saco e' weas | chuchetumadre")
        chilean_cfg.add_prod("WHORE", "puta | maraca | la tragaleche | la comesables")
        chilean_cfg.add_prod("PLACE", "chucha | mierda | cresta | conchetumadre")

        self.insult_cfgs["soft"] = soft_cfg
        self.insult_cfgs["shakespeare"] = shakespeare_cfg
        self.insult_cfgs["python"] = python_cfg
        self.insult_cfgs["normal"] = normal_cfg
        self.insult_cfgs["trava"] = trava_cfg
        self.insult_cfgs["chilean"] = chilean_cfg

    def get_insult(self, mode="normal"):
        if mode not in self.insult_cfgs:
            mode = "normal"

        return self.insult_cfgs[mode].gen_random("S")


class CFG(object):
    def __init__(self):
        self.prod = defaultdict(list)
        self.bound_functions = dict()

    def add_prod(self, lhs, rhs):
        """ Add production to the grammar. 'rhs' can
            be several productions separated by '|'.
            Each production is a sequence of symbols
            separated by whitespace.

            Usage:
                grammar.add_prod('NT', 'VP PP')
                grammar.add_prod('Digit', '1|2|3|4')
        """
        prods = rhs.split('|')
        for prod in prods:
            self.prod[lhs].append(tuple(prod.split()))

    def bind(self, binding_id, binding_fun):
        self.bound_functions[binding_id] = binding_fun

    def gen_random(self,
                   symbol,
                   cfactor=0.25):
        return re.sub(r'\s+([?,.!"])', r'\1', self.gen_random_convergent(symbol, cfactor)).strip()

    def gen_random_convergent(self,
                              symbol,
                              cfactor=0.25,
                              pcount=defaultdict(int)
                              ):
        """ Generate a random sentence from the
            grammar, starting with the given symbol.

            Uses a convergent algorithm - productions
            that have already appeared in the
            derivation on each branch have a smaller
            chance to be selected.

            cfactor - controls how tight the
            convergence is. 0 < cfactor < 1.0

            pcount is used internally by the
            recursive calls to pass on the
            productions that have been used in the
            branch.
        """
        sentence = ''

        # The possible productions of this symbol are weighted
        # by their appearance in the branch that has led to this
        # symbol in the derivation
        #
        weights = []
        for prod in self.prod[symbol]:
            if prod in pcount:
                weights.append(cfactor ** (pcount[prod]))
            else:
                weights.append(1.0)

        rand_prod = self.prod[symbol][weighted_choice(weights)]

        # pcount is a single object (created in the first call to
        # this method) that's being passed around into recursive
        # calls to count how many times productions have been
        # used.
        # Before recursive calls the count is updated, and after
        # the sentence for this call is ready, it is rolled-back
        # to avoid modifying the parent's pcount.
        #
        pcount[rand_prod] += 1

        for sym in rand_prod:
            # for non-terminals, recurse
            if sym in self.prod:
                sentence += self.gen_random_convergent(
                    sym,
                    cfactor=cfactor,
                    pcount=pcount)
            else:
                if sym.startswith("_") and sym[1:] in self.bound_functions:
                    sentence += self.bound_functions[sym[1:]]() + ' '
                else:
                    sentence += sym + ' '

                    # backtracking: clear the modification to pcount
        pcount[rand_prod] -= 1
        return sentence


def weighted_choice(weights):
    rnd = random.random() * sum(weights)
    for idx, w in enumerate(weights):
        rnd -= w
        if rnd < 0:
            return idx


if __name__ == "__main__":
    with Insulter("insults.json") as insulter:
        print(insulter.modes())
        for i in range(30):
            print(insulter.get_insult("python"))
