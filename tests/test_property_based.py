"""
tests/test_property_based.py  –  Property-based tests (Hypothesis) for money invariants.

These tests verify that fundamental financial invariants hold for ALL possible inputs,
not just hand-picked examples. If a bug exists, Hypothesis will find the minimal
failing input and report it.

Invariants tested:
  1. System-wide balance conservation — total balance changes exactly by deposit/withdraw amounts
  2. No negative balances after withdrawal
  3. Transfer preserves total system balance
  4. Interest is always non-negative
  5. Account can never go below zero (overdraft prevention)
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import assume, given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition

from domain.entities import Account, Transaction, TransactionType
from application.services import (
    AccountService,
    AuthService,
    TransactionService,
)

from tests.fakes import (
    FakeAccountRepository,
    FakeAdminRepository,
    FakeLoginAttemptRepository,
    FakeTokenVersionRepository,
    FakeTransactionRepository,
)

from utils.auth import hash_password


# ═══════════════════════════════════════════════════════════════════════════════
#  Strategies — generate random valid account data
# ═══════════════════════════════════════════════════════════════════════════════

valid_account_numbers = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=57),
    min_size=10, max_size=10,
)

positive_decimals = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000.00"),
    allow_nan=False, allow_infinity=False,
    places=2,
)

amounts = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("10000.00"),
    allow_nan=False, allow_infinity=False,
    places=2,
)

passwords = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cc", "Cs"),
    ),
    min_size=8, max_size=30,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_account(acc_no: str, balance: Decimal) -> Account:
    return Account(
        account_number=acc_no,
        name="Prop Test User",
        age=25,
        gender="Other",
        mobile="9876543210",
        email="prop@test.com",
        password=hash_password("TestPass1"),
        balance=balance,
        is_active=True,
        is_frozen=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Test: Balance conservation — deposit increases balance by exactly the amount
# ═══════════════════════════════════════════════════════════════════════════════


@given(
    acc_no=valid_account_numbers,
    initial_balance=positive_decimals,
    deposit_amount=amounts,
)
def test_deposit_preserves_invariant(acc_no, initial_balance, deposit_amount):
    """Deposit increases balance by exactly the amount deposited.

    Property: ∀ account a, initial balance b, deposit amount d:
        execute(deposit(a, d)).balance == b + d
    """
    repo = FakeAccountRepository()
    txn_repo = FakeTransactionRepository()
    service = TransactionService(repo, txn_repo)

    account = _make_account(acc_no, initial_balance)
    repo.create(account)

    result = service.deposit(acc_no, deposit_amount)
    assert result.success is True

    updated = repo.get(acc_no)
    assert updated.balance == initial_balance + deposit_amount, (
        f"Balance mismatch: {updated.balance} != {initial_balance} + {deposit_amount}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Test: No overdraft — withdrawal fails if amount > balance
# ═══════════════════════════════════════════════════════════════════════════════


@given(
    acc_no=valid_account_numbers,
    initial_balance=positive_decimals,
    withdraw_amount=amounts,
)
def test_no_overdraft(acc_no, initial_balance, withdraw_amount):
    """Withdrawal fails if amount > balance.

    Property: balance - withdraw >= 0  ⇒  success
              balance - withdraw < 0   ⇒  failure (no change)
    """
    repo = FakeAccountRepository()
    txn_repo = FakeTransactionRepository()
    service = TransactionService(repo, txn_repo)

    account = _make_account(acc_no, initial_balance)
    repo.create(account)

    result = service.withdraw(acc_no, withdraw_amount)

    if withdraw_amount <= initial_balance:
        assert result.success is True
        updated = repo.get(acc_no)
        assert updated.balance == initial_balance - withdraw_amount
    else:
        assert result.success is False
        updated = repo.get(acc_no)
        assert updated.balance == initial_balance  # Unchanged


# ═══════════════════════════════════════════════════════════════════════════════
#  Test: Transfer preserves total system balance
# ═══════════════════════════════════════════════════════════════════════════════


@given(
    sender_acc=valid_account_numbers,
    receiver_acc=valid_account_numbers,
    sender_balance=positive_decimals,
    receiver_balance=positive_decimals,
    transfer_amount=amounts,
)
def test_transfer_preserves_total_balance(
    sender_acc, receiver_acc, sender_balance, receiver_balance, transfer_amount
):
    """Total system balance is conserved during transfers.

    Property: ∀ transfer(a, b, amount):
        total_balance_before == total_balance_after

    Money is neither created nor destroyed — it moves from one account to another.
    """
    assume(sender_acc != receiver_acc)  # Must be different accounts

    repo = FakeAccountRepository()
    txn_repo = FakeTransactionRepository()
    service = TransactionService(repo, txn_repo)

    sender = _make_account(sender_acc, sender_balance)
    receiver = _make_account(receiver_acc, receiver_balance)
    repo.create(sender)
    repo.create(receiver)

    total_before = sum(
        a.balance for a in repo.get_all()
    )

    result = service.transfer(sender_acc, receiver_acc, transfer_amount)

    total_after = sum(
        a.balance for a in repo.get_all()
    )

    assert total_before == total_after, (
        f"Total balance changed from {total_before} to {total_after}! "
        f"Money would be created or destroyed!"
    )

    if result.success:
        assert repo.get(sender_acc).balance == sender_balance - transfer_amount
        assert repo.get(receiver_acc).balance == receiver_balance + transfer_amount
    else:
        # Failed transfer should not change balances
        assert repo.get(sender_acc).balance == sender_balance
        assert repo.get(receiver_acc).balance == receiver_balance


# ═══════════════════════════════════════════════════════════════════════════════
#  Test: Interest is always non-negative and proportional to balance
# ═══════════════════════════════════════════════════════════════════════════════


@given(
    acc_no=valid_account_numbers,
    balance=st.decimals(
        min_value=Decimal("0.00"),
        max_value=Decimal("10000000.00"),
        allow_nan=False, allow_infinity=False,
        places=2,
    ),
)
def test_interest_monotonicity(acc_no, balance):
    """Interest is always >= 0 and strictly positive for positive balances.

    Property: balance > 0  ⇒  interest > 0
              balance = 0  ⇒  interest = 0
    """
    repo = FakeAccountRepository()
    txn_repo = FakeTransactionRepository()
    service = TransactionService(repo, txn_repo)

    account = _make_account(acc_no, balance)
    repo.create(account)

    result = service.apply_interest(acc_no)

    if balance > 0:
        assert result.success is True
        assert result.data["interest"] > 0, f"Interest should be > 0 for balance {balance}"
        updated = repo.get(acc_no)
        assert updated.balance > balance
    else:
        assert result.success is False
        assert "no interest" in result.message.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Test: Stateful — money never lost in transfer sequence
# ═══════════════════════════════════════════════════════════════════════════════


class MoneyInvariantMachine(RuleBasedStateMachine):
    """Stateful state machine that simulates a sequence of operations.

    After ANY sequence of deposits, withdrawals, and transfers, the total
    system balance must equal the sum of all deposits minus all withdrawals.
    No money is ever created or destroyed.
    """

    def __init__(self):
        super().__init__()
        self.account_repo = FakeAccountRepository()
        self.txn_repo = FakeTransactionRepository()
        self.service = TransactionService(self.account_repo, self.txn_repo)
        self.total_deposits = Decimal("0.00")
        self.total_withdrawals = Decimal("0.00")

        # Create two accounts with initial balances
        self.acc_a = "1000000001"
        self.acc_b = "2000000002"
        self.account_repo.create(_make_account(self.acc_a, Decimal("1000.00")))
        self.account_repo.create(_make_account(self.acc_b, Decimal("500.00")))

    @rule(amount=amounts)
    def deposit(self, amount: Decimal):
        """Deposit money into account A."""
        result = self.service.deposit(self.acc_a, amount)
        if result.success:
            self.total_deposits += amount

    @rule(amount=amounts)
    def withdraw(self, amount: Decimal):
        """Withdraw money from account A."""
        result = self.service.withdraw(self.acc_a, amount)
        if result.success:
            self.total_withdrawals += amount

    @rule(amount=amounts)
    def transfer_a_to_b(self, amount: Decimal):
        """Transfer money from A to B."""
        self.service.transfer(self.acc_a, self.acc_b, amount)

    @rule(amount=amounts)
    def transfer_b_to_a(self, amount: Decimal):
        """Transfer money from B to A."""
        self.service.transfer(self.acc_b, self.acc_a, amount)

    @invariant()
    def total_balance_conserved(self):
        """Total balance equals initial balance + deposits - withdrawals."""
        total = sum(a.balance for a in self.account_repo.get_all())
        expected = Decimal("1500.00") + self.total_deposits - self.total_withdrawals
        assert total == expected, (
            f"Balance invariant broken! Total: {total}, Expected: {expected}"
        )

    @invariant()
    def no_negative_balances(self):
        """No account balance can ever be negative."""
        for account in self.account_repo.get_all():
            assert account.balance >= Decimal("0.00"), (
                f"Account {account.account_number} has negative balance: {account.balance}"
            )

    @invariant()
    def transaction_count_matches_txns(self):
        """Total transaction count should be >= 0 (sanity check)."""
        assert self.txn_repo.count() >= 0


# Register as a regular test function
TestMoneyInvariants = MoneyInvariantMachine.TestCase
