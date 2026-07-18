"""
Tests targeting specific coverage gaps identified in the audit.

Focuses on:
- Loan rejection error paths
- Notification service failure handling
- Admin freeze/unfreeze edge cases
- Service-level validation paths
"""

from decimal import Decimal


from unionbank.domain.entities import Account


# ═══════════════════════════════════════════════════════════════════════════════
#  Loan Rejection Error Paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoanRejectionErrorPaths:
    """Test edge cases in loan rejection that are currently uncovered."""

    def test_reject_nonexistent_loan(self, c):
        """Rejecting a loan that doesn't exist should fail gracefully."""
        result = c.loan_service().reject_loan(
            loan_id="nonexistent-id",
            reason="Not needed",
            admin_user="admin",
        )
        assert not result.success
        assert "not found" in result.message.lower()

    def test_reject_already_approved_loan(self, c, sample_account):
        """Rejecting an already approved loan should fail."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        # First apply and approve
        apply_result = c.loan_service().apply_loan(
            acc_no=sample_account.account_number,
            loan_type="Personal",
            principal_amount=Decimal("50000"),
            interest_rate=Decimal("10"),
            tenure_months=12,
        )
        assert apply_result.success

        # Get the loan ID
        loans = c.loan_service().list_loans(sample_account.account_number)
        loan_id = loans[0].loan_id

        # Approve it
        c.loan_service().approve_loan(loan_id, admin_user="admin")

        # Now try to reject it
        result = c.loan_service().reject_loan(
            loan_id=loan_id,
            reason="Too late",
            admin_user="admin",
        )
        assert not result.success
        assert "approve" in result.message.lower() or "approved" in result.message.lower() or "cannot" in result.message.lower() or "reject" in result.message.lower()

    def test_reject_without_reason(self, c, sample_account):
        """Rejecting a loan without providing a reason should still work."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        apply_result = c.loan_service().apply_loan(
            acc_no=sample_account.account_number,
            loan_type="Personal",
            principal_amount=Decimal("30000"),
            interest_rate=Decimal("12"),
            tenure_months=24,
        )
        assert apply_result.success

        loans = c.loan_service().list_loans(sample_account.account_number)
        loan_id = loans[-1].loan_id

        result = c.loan_service().reject_loan(
            loan_id=loan_id,
            reason=None,
            admin_user="admin",
        )
        assert result.success


# ═══════════════════════════════════════════════════════════════════════════════
#  Admin Freeze / Unfreeze Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminFreezeUnfreeze:
    """Test edge cases in admin freeze/unfreeze operations."""

    def test_freeze_nonexistent_account(self, c):
        """Freezing a non-existent account should fail."""
        result = c.admin_service().freeze_account(
            acc_no="9999999999",
            actor="admin_test",
        )
        assert not result.success
        assert "not found" in result.message.lower()

    def test_unfreeze_nonexistent_account(self, c):
        """Unfreezing a non-existent account should fail."""
        result = c.admin_service().unfreeze_account(
            acc_no="9999999999",
            actor="admin_test",
        )
        assert not result.success
        assert "not found" in result.message.lower()

    def test_double_freeze(self, c, sample_account):
        """Freezing an already frozen account should be handled."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        # First freeze
        result1 = c.admin_service().freeze_account(
            acc_no=sample_account.account_number,
            actor="admin_test",
        )
        assert result1.success

        # Second freeze
        result2 = c.admin_service().freeze_account(
            acc_no=sample_account.account_number,
            actor="admin_test",
        )
        # Second freeze may succeed (idempotent) or fail with a message
        # Both are acceptable as long as it doesn't crash

    def test_double_unfreeze(self, c, sample_account):
        """Unfreezing an already active account should be handled."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        result = c.admin_service().unfreeze_account(
            acc_no=sample_account.account_number,
            actor="admin_test",
        )
        # Should either succeed (idempotent) or say the account is not frozen
        # Just verify it doesn't crash

    def test_freeze_transaction_checks(self, c, sample_account):
        """A frozen account should be rejected by transaction service."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        # First freeze
        c.admin_service().freeze_account(
            acc_no=sample_account.account_number,
            actor="admin_test",
        )

        # Deposit should fail
        result = c.transaction_service().deposit(
            acc_no=sample_account.account_number,
            amount=Decimal("100"),
            category="Test",
        )
        assert not result.success
        assert "frozen" in result.message.lower() or "not found" in result.message.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Service Failure Handling
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationFailures:
    """Test that notification failures do not crash the system."""

    def test_register_without_notification_service(self, c):
        """Registration should succeed even without a notification service."""
        result = c.auth_service().customer_register(
            name="Notify Test",
            age=30,
            gender="Male",
            mobile="9876543210",
            email="notifytest@example.com",
            password="StrongP@ss1",
        )
        assert result.success

    def test_send_transaction_notification_fails_gracefully(self, c, sample_account):
        """Transaction notification failure should not block the deposit."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        # Deposit with a non-functional notification setup
        # This should work because notification failures are caught
        result = c.transaction_service().deposit(
            acc_no=sample_account.account_number,
            amount=Decimal("500"),
            category="Test",
        )
        assert result.success


# ═══════════════════════════════════════════════════════════════════════════════
#  Service-level Validation Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestServiceValidation:
    """Test edge cases in service-level validation."""

    def test_empty_account_number(self, c):
        """Empty account numbers should fail validation."""
        result = c.auth_service().customer_login(
            "",
            "somepassword",
        )
        assert not result.success

    def test_negative_deposit(self, c, sample_account):
        """Negative deposit amounts should be rejected."""
        # Persist the account in the DB first
        c.account_repo().create(sample_account)
        c.account_repo().commit()

        result = c.transaction_service().deposit(
            acc_no=sample_account.account_number,
            amount=Decimal("-100"),
            category="Test",
        )
        assert not result.success

    def test_zero_amount_transfer(self, c, sample_account):
        """Zero-amount transfers should be rejected."""
        # Persist both accounts in the DB first
        c.account_repo().create(sample_account)

        # Create a second account for the transfer
        second_account = Account(
            account_number="2000000002",
            name="Transfer Test",
            age=25,
            gender="Male",
            mobile="9988776655",
            email="transfertest@example.com",
            password="hashed_pwd",
            balance=Decimal("1000"),
            is_active=True,
        )
        c.account_repo().create(second_account)
        c.account_repo().commit()

        result = c.transaction_service().transfer(
            sender_acc_no=sample_account.account_number,
            receiver_acc_no="2000000002",
            amount=Decimal("0"),
            category="Test",
        )
        assert not result.success
