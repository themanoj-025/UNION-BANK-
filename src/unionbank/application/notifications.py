"""application/notifications.py  –  Notification service for Union Bank.

Provides in-app notification creation, email/SMS alert delivery,
and preference management. Integrates with existing service hooks
via an optional dependency pattern (same as audit_log_repo).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import Notification, NotificationPreference, ServiceResult
from unionbank.utils.formatting import fmt_currency, generate_notification_id

from .interfaces import (
    AccountRepositoryProtocol,
    NotificationPreferenceRepositoryProtocol,
    NotificationRepositoryProtocol,
    NotificationSenderProtocol,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  Log-based Notification Sender (no external provider required)
# ═══════════════════════════════════════════════════════════════════════════════


class LogNotificationSender:
    """Notification sender that logs to the application logger.

    This is the default sender — it logs email/SMS alerts instead of
    actually sending them. When real email/SMS providers are configured
    (SMTP, Twilio, etc.), swap this with a concrete implementation.
    """

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Simulate sending an email by logging it."""
            from unionbank.utils.logger import logger
            logger.info(
                f"[EMAIL] To: {to_email} | Subject: {subject} | Body: {body[:200]}"
            )
        return True

    def send_sms(self, to_phone: str, message: str) -> bool:
        """Simulate sending an SMS by logging it."""
            from unionbank.utils.logger import logger
            logger.info(
                f"[SMS] To: {to_phone} | Message: {message[:160]}"
            )
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  Notification Service
# ═══════════════════════════════════════════════════════════════════════════════

NOTIFICATION_TYPES = [
    "deposit", "withdraw", "transfer_sent", "transfer_received",
    "interest", "loan_approved", "loan_rejected", "loan_emi_paid",
    "loan_closed", "account_frozen", "account_unfrozen", "account_closed",
    "goal_completed", "welcome",
]


class NotificationService:
    """Create and manage in-app notifications and alert delivery."""

    def __init__(
        self,
        notif_repo: NotificationRepositoryProtocol,
        pref_repo: NotificationPreferenceRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        sender: Optional[NotificationSenderProtocol] = None,
    ):
        self.notif_repo = notif_repo
        self.pref_repo = pref_repo
        self.account_repo = account_repo
        self.sender = sender or LogNotificationSender()

    # ── Preference management ───────────────────────────────────────────────

    def get_preferences(self, acc_no: str) -> NotificationPreference:
        """Get notification preferences for an account (creates defaults if missing)."""
        pref = self.pref_repo.get(acc_no)
        if pref is None:
            pref = NotificationPreference(account_number=acc_no)
            self.pref_repo.create_or_update(pref)
            self.pref_repo.commit()
        return pref

    def update_preferences(self, acc_no: str, **kwargs) -> ServiceResult:
        """Update notification preferences for an account."""
        pref = self.get_preferences(acc_no)
        for key, value in kwargs.items():
            if hasattr(pref, key) and value is not None:
                setattr(pref, key, value)
        self.pref_repo.create_or_update(pref)
        self.pref_repo.commit()
        return ServiceResult(success=True, message="Notification preferences updated.")

    # ── Notification creation ───────────────────────────────────────────────

    def notify(
        self,
        acc_no: str,
        notif_type: str,
        title: str,
        message: str,
        related_txn_id: Optional[str] = None,
    ) -> Notification:
        """Create an in-app notification and send alerts based on preferences.

        Returns the created Notification entity (without committing —
        caller must commit).
        """
        notification = Notification(
            notif_id=generate_notification_id(),
            account_number=acc_no,
            type=notif_type,
            title=title,
            message=message,
            is_read=False,
            created_at=_utcnow(),
            related_txn_id=related_txn_id,
        )
        self.notif_repo.create(notification)

        # Send channel alerts based on preferences
        self._send_alerts(acc_no, title, message)

        return notification

    def notify_and_commit(
        self,
        acc_no: str,
        notif_type: str,
        title: str,
        message: str,
        related_txn_id: Optional[str] = None,
    ) -> Notification:
        """Create notification and commit immediately."""
        notif = self.notify(acc_no, notif_type, title, message, related_txn_id)
        self.notif_repo.commit()
        return notif

    def _send_alerts(self, acc_no: str, title: str, message: str) -> None:
        """Send email/SMS alerts based on account preferences."""
        try:
            pref = self.get_preferences(acc_no)
            account = self.account_repo.get(acc_no)
            if account is None:
                return

            if pref.email_enabled and account.email:
                self.sender.send_email(
                    to_email=account.email,
                    subject=f"Union Bank: {title}",
                    body=message,
                )

            if pref.sms_enabled and account.mobile:
                self.sender.send_sms(
                    to_phone=account.mobile,
                    message=f"Union Bank: {title} - {message[:120]}",
                )
        except Exception:
            from unionbank.utils.logger import logger
            logger.warning(f"Failed to send alerts for {acc_no}", exc_info=True)

    # ── Convenience methods for common notification types ───────────────────

    def notify_deposit(
        self, acc_no: str, amount: Decimal, balance: Decimal,
        txn_id: str,
    ) -> Notification:
        title = "Deposit Received"
        message = (
            f"{fmt_currency(float(amount))} has been deposited into your account. "
            f"New balance: {fmt_currency(float(balance))}"
        )
        return self.notify_and_commit(acc_no, "deposit", title, message, txn_id)

    def notify_withdraw(
        self, acc_no: str, amount: Decimal, balance: Decimal,
        txn_id: str,
    ) -> Notification:
        title = "Withdrawal Processed"
        message = (
            f"{fmt_currency(float(amount))} has been withdrawn from your account. "
            f"New balance: {fmt_currency(float(balance))}"
        )
        return self.notify_and_commit(acc_no, "withdraw", title, message, txn_id)

    def notify_transfer_sent(
        self, acc_no: str, amount: Decimal, target_acc: str,
        balance: Decimal, txn_id: str,
    ) -> Notification:
        title = "Transfer Sent"
        message = (
            f"{fmt_currency(float(amount))} transferred to account {target_acc}. "
            f"New balance: {fmt_currency(float(balance))}"
        )
        return self.notify_and_commit(acc_no, "transfer_sent", title, message, txn_id)

    def notify_transfer_received(
        self, acc_no: str, amount: Decimal, from_acc: str,
        balance: Decimal, txn_id: str,
    ) -> Notification:
        title = "Transfer Received"
        message = (
            f"{fmt_currency(float(amount))} received from account {from_acc}. "
            f"New balance: {fmt_currency(float(balance))}"
        )
        return self.notify_and_commit(acc_no, "transfer_received", title, message, txn_id)

    def notify_interest(
        self, acc_no: str, amount: Decimal, balance: Decimal,
        txn_id: str,
    ) -> Notification:
        title = "Interest Credited"
        message = (
            f"Interest of {fmt_currency(float(amount))} has been credited to your account. "
            f"New balance: {fmt_currency(float(balance))}"
        )
        return self.notify_and_commit(acc_no, "interest", title, message, txn_id)

    def notify_loan_approved(
        self, acc_no: str, amount: Decimal, loan_type: str, loan_id: str,
    ) -> Notification:
        title = "Loan Approved 🎉"
        message = (
            f"Your {loan_type} loan of {fmt_currency(float(amount))} has been approved "
            f"and disbursed to your account. (Loan ID: {loan_id})"
        )
        return self.notify_and_commit(acc_no, "loan_approved", title, message, loan_id)

    def notify_loan_rejected(
        self, acc_no: str, loan_type: str, loan_id: str, reason: str = "",
    ) -> Notification:
        title = "Loan Application Rejected"
        message = (
            f"Your {loan_type} loan application ({loan_id}) has been rejected."
            + (f" Reason: {reason}" if reason else "")
        )
        return self.notify_and_commit(acc_no, "loan_rejected", title, message, loan_id)

    def notify_emi_paid(
        self, acc_no: str, amount: Decimal, loan_type: str, loan_id: str,
        remaining: Decimal,
    ) -> Notification:
        title = "EMI Payment Confirmed"
        message = (
            f"EMI of {fmt_currency(float(amount))} paid for your {loan_type} loan. "
            f"Remaining: {fmt_currency(float(remaining))} (Loan ID: {loan_id})"
        )
        return self.notify_and_commit(acc_no, "loan_emi_paid", title, message, loan_id)

    def notify_loan_closed(
        self, acc_no: str, loan_type: str, loan_id: str,
    ) -> Notification:
        title = "Loan Fully Paid 🎉"
        message = (
            f"Congratulations! Your {loan_type} loan ({loan_id}) has been fully paid off!"
        )
        return self.notify_and_commit(acc_no, "loan_closed", title, message, loan_id)

    def notify_account_frozen(
        self, acc_no: str, reason: str = "",
    ) -> Notification:
        title = "Account Frozen"
        message = (
            "Your account has been frozen by the bank."
            + (f" Reason: {reason}" if reason else " Please contact support.")
        )
        return self.notify_and_commit(acc_no, "account_frozen", title, message)

    def notify_account_unfrozen(self, acc_no: str) -> Notification:
        title = "Account Unfrozen"
        message = "Your account has been unfrozen. You can now transact normally."
        return self.notify_and_commit(acc_no, "account_unfrozen", title, message)

    def notify_welcome(self, acc_no: str) -> Notification:
        title = "Welcome to Union Bank! 🏦"
        message = (
            "Thank you for opening an account with Union Bank. "
            "You can now deposit, withdraw, transfer funds, and much more!"
        )
        return self.notify_and_commit(acc_no, "welcome", title, message)
