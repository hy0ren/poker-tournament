"""Basic tests for the poker tournament package."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from poker_tournament.card import Card, Deck
from poker_tournament.hand_eval import evaluate_hand, hand_name
from poker_tournament.player import Player
from poker_tournament.game import PokerGame
from poker_tournament.bot_loader import load_bot, load_bots_from_directory
from poker_tournament.tournament import Tournament


# ---------------------------------------------------------------------------
# Card tests
# ---------------------------------------------------------------------------

def test_card_repr():
    assert repr(Card(14, 'h')) == 'A♥'
    assert repr(Card(13, 's')) == 'K♠'
    assert repr(Card(10, 'd')) == 'T♦'
    assert repr(Card(2, 'c')) == '2♣'


def test_deck_size():
    d = Deck()
    assert len(d) == 52


def test_deck_deal_one():
    d = Deck()
    card = d.deal()
    assert isinstance(card, Card)
    assert len(d) == 51


def test_deck_deal_many():
    d = Deck()
    cards = d.deal(5)
    assert len(cards) == 5
    assert len(d) == 47


# ---------------------------------------------------------------------------
# Hand evaluation tests
# ---------------------------------------------------------------------------

def c(rank, suit):
    return Card(rank, suit)


def test_high_card():
    cards = [c(2,'h'), c(4,'d'), c(6,'s'), c(8,'c'), c(10,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 0, "Expected high card"


def test_one_pair():
    cards = [c(2,'h'), c(2,'d'), c(6,'s'), c(8,'c'), c(10,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 1, "Expected one pair"


def test_two_pair():
    cards = [c(2,'h'), c(2,'d'), c(6,'s'), c(6,'c'), c(10,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 2, "Expected two pair"


def test_three_of_a_kind():
    cards = [c(2,'h'), c(2,'d'), c(2,'s'), c(6,'c'), c(10,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 3, "Expected three of a kind"


def test_straight():
    cards = [c(5,'h'), c(6,'d'), c(7,'s'), c(8,'c'), c(9,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 4, "Expected straight"


def test_wheel_straight():
    cards = [c(14,'h'), c(2,'d'), c(3,'s'), c(4,'c'), c(5,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 4, "Expected wheel straight"
    assert score[1] == 5, "Wheel high card should be 5"


def test_flush():
    cards = [c(2,'h'), c(5,'h'), c(7,'h'), c(9,'h'), c(11,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 5, "Expected flush"


def test_full_house():
    cards = [c(3,'h'), c(3,'d'), c(3,'s'), c(7,'c'), c(7,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 6, "Expected full house"


def test_four_of_a_kind():
    cards = [c(9,'h'), c(9,'d'), c(9,'s'), c(9,'c'), c(5,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 7, "Expected four of a kind"


def test_straight_flush():
    cards = [c(5,'h'), c(6,'h'), c(7,'h'), c(8,'h'), c(9,'h')]
    score = evaluate_hand(cards)
    assert score[0] == 8, "Expected straight flush"


def test_best_from_seven():
    cards = [
        c(9,'h'), c(9,'d'),
        c(9,'s'), c(9,'c'), c(5,'h'), c(2,'d'), c(3,'s'),
    ]
    score = evaluate_hand(cards)
    assert score[0] == 7, "Expected four-of-a-kind from 7 cards"


def test_hand_ordering():
    royal_flush = evaluate_hand([c(10,'s'), c(11,'s'), c(12,'s'), c(13,'s'), c(14,'s')])
    full_house = evaluate_hand([c(3,'h'), c(3,'d'), c(3,'s'), c(7,'c'), c(7,'h')])
    one_pair = evaluate_hand([c(2,'h'), c(2,'d'), c(6,'s'), c(8,'c'), c(10,'h')])
    assert royal_flush > full_house > one_pair


# ---------------------------------------------------------------------------
# Game tests
# ---------------------------------------------------------------------------

def always_call(gs):
    if gs['call_amount'] == 0:
        return ('check', 0)
    return ('call', 0)


def always_fold(gs):
    return ('fold', 0)


def test_single_hand_no_crash():
    players = [
        Player("Alice", 500, always_call),
        Player("Bob",   500, always_call),
    ]
    game = PokerGame(players, verbose=False)
    result = game.play_hand()
    assert result is not None
    total = sum(p.stack for p in players)
    assert total == 1000, f"Chips should be conserved, got {total}"


def test_folder_loses_blind():
    players = [
        Player("Folder", 500, always_fold),
        Player("Caller", 500, always_call),
    ]
    game = PokerGame(players, verbose=False)
    result = game.play_hand()
    assert result is not None
    assert sum(p.stack for p in players) == 1000


def test_chip_conservation_many_hands():
    players = [
        Player("A", 500, always_call),
        Player("B", 500, always_call),
        Player("C", 500, always_call),
    ]
    game = PokerGame(players, verbose=False)
    for _ in range(20):
        active = [p for p in players if p.stack > 0]
        if len(active) < 2:
            break
        game.play_hand()
    total = sum(p.stack for p in players)
    assert total == 1500, f"Total chips should be 1500, got {total}"


def test_side_pot_calculation():
    game = PokerGame([], verbose=False)

    class FakePlayer:
        def __init__(self, name, total_bet, folded=False):
            self.name = name
            self.total_bet = total_bet
            self.folded = folded

    a  = FakePlayer("A", 50,  folded=False)
    b  = FakePlayer("B", 100, folded=False)
    cf = FakePlayer("C", 100, folded=True)

    pots = game._calculate_side_pots([a, b, cf])
    assert len(pots) == 2
    main_pot, main_eligible = pots[0]
    side_pot, side_eligible = pots[1]
    assert main_pot == 150
    assert {p.name for p in main_eligible} == {"A", "B"}
    assert side_pot == 100
    assert {p.name for p in side_eligible} == {"B"}


# ---------------------------------------------------------------------------
# Bot loader tests
# ---------------------------------------------------------------------------

BOTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'bots')


def test_load_single_bot():
    name, func = load_bot(os.path.join(BOTS_DIR, 'call_bot.py'))
    assert name == 'CallBot'
    assert callable(func)


def test_load_directory():
    bots = load_bots_from_directory(BOTS_DIR)
    assert len(bots) == 4
    names = [n for n, _ in bots]
    assert 'CallBot' in names
    assert 'RandomBot' in names


def test_bot_interface():
    bots = load_bots_from_directory(BOTS_DIR)

    sample_state = {
        'hole_cards':      [Card(14, 'h'), Card(13, 's')],
        'community_cards': [Card(10, 'h'), Card(11, 'h'), Card(12, 'h')],
        'pot':             100,
        'current_bet':     20,
        'call_amount':     20,
        'min_raise':       40,
        'stack':           480,
        'my_bet':          0,
        'round':           'flop',
        'players':         [{'name': 'Other', 'stack': 480, 'bet': 20,
                              'total_bet': 20, 'folded': False, 'all_in': False}],
        'big_blind':       20,
        'small_blind':     10,
    }

    valid_actions = {'fold', 'check', 'call', 'raise'}
    for name, func in bots:
        result = func(sample_state)
        assert isinstance(result, (list, tuple)) and len(result) == 2, \
            f"{name} returned invalid result: {result!r}"
        action, amount = result
        assert action in valid_actions, \
            f"{name} returned unknown action: {action!r}"
        assert isinstance(amount, (int, float)), \
            f"{name} returned non-numeric amount: {amount!r}"


# ---------------------------------------------------------------------------
# Tournament tests
# ---------------------------------------------------------------------------

def test_elimination_tournament():
    bots = load_bots_from_directory(BOTS_DIR)
    t = Tournament(bots, starting_chips=500, verbose=False)
    standings = t.run()
    assert len(standings) == len(bots)
    assert standings[0]['rank'] == 1
    assert standings[0]['chips'] > 0
    total = sum(e['chips'] for e in standings)
    assert total == 500 * len(bots), f"Chips not conserved: {total}"


def test_fixed_tournament():
    bots = load_bots_from_directory(BOTS_DIR)
    t = Tournament(bots, starting_chips=500, mode='fixed',
                   num_hands=20, verbose=False)
    standings = t.run()
    assert len(standings) == len(bots)
    assert standings[0]['rank'] == 1


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import traceback

    tests = [
        test_card_repr, test_deck_size, test_deck_deal_one, test_deck_deal_many,
        test_high_card, test_one_pair, test_two_pair, test_three_of_a_kind,
        test_straight, test_wheel_straight, test_flush, test_full_house,
        test_four_of_a_kind, test_straight_flush, test_best_from_seven,
        test_hand_ordering,
        test_single_hand_no_crash, test_folder_loses_blind,
        test_chip_conservation_many_hands, test_side_pot_calculation,
        test_load_single_bot, test_load_directory, test_bot_interface,
        test_elimination_tournament, test_fixed_tournament,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
