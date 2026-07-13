"""
account.py  –  Account model + all account-level operations (with logging).
"""

import os
from datetime import datetime, timezone

from utils import (
    load_json, save_json,
    generate_account_number, generate_transaction_id,
    now_str, fmt_currency,
    get_float, get_int,
    hash_password, verify_password, validate_password,
    validate_email, validate_phone, validate_name,
    get_category_choice, export_transactions_to_csv,
    generate_csv_filename, calculate_monthly_interest,
    load_goals, save_goals, generate_goal_id,
    ACCOUNTS_FILE, TRANSACTIONS_FILE,
)
from ui import header, divider, success, error, warning, info, prompt_password, GREEN, RED, CYAN, WHITE, YELLOW, BOLD, RESET
from logger import logger
from services import (
    process_deposit, process_withdraw, process_transfer,
    process_close_account, process_apply_interest,
    create_savings_goal, contribute_to_goal, delete_savings_goal,
)
from database import init_db

def _utcnow():
    return datetime.now(timezone.utc)

# Ensure SQLite tables exist
init_db()


class Account:

    def __init__(self, data: dict):
        self.account_number = data["account_number"]
        self.name           = data["name"]
        self.age            = data["age"]
        self.gender         = data["gender"]
        self.mobile         = data["mobile"]
        self.email          = data["email"]
        self.password       = data["password"]
        self.balance        = data.get("balance", 0.0)
        self.is_active      = data.get("is_active", True)
        self.is_frozen      = data.get("is_frozen", False)
        self.created_at     = data.get("created_at", now_str())

    def to_dict(self):
        return {
            "account_number": self.account_number,
            "name":           self.name,
            "age":            self.age,
            "gender":         self.gender,
            "mobile":         self.mobile,
            "email":          self.email,
            "password":       self.password,
            "balance":        self.balance,
            "is_active":      self.is_active,
            "is_frozen":      self.is_frozen,
            "created_at":     self.created_at,
        }

    def save(self):
        """Save the account — writes to SQLite only (no JSON)."""
        from datetime import datetime
        from decimal import Decimal
        from container import get_container
        from domain.entities import Account as DomainAccount

        c = get_container()
        repo = c.account_repo()

        # Preserve original created_at if account already exists
        existing = repo.get(self.account_number)
        original_created_at = None
        if existing:
            original_created_at = existing.created_at

        # Parse string created_at to datetime if it's a string
        created_at_dt = None
        if isinstance(self.created_at, str) and self.created_at:
            try:
                created_at_dt = datetime.fromisoformat(self.created_at.replace(" ", "T"))
            except (ValueError, TypeError):
                pass

        domain_acc = DomainAccount(
            account_number=self.account_number,
            name=self.name,
            age=self.age,
            gender=self.gender,
            mobile=self.mobile,
            email=self.email,
            password=self.password,
            balance=Decimal(str(self.balance)),
            is_active=self.is_active,
            is_frozen=self.is_frozen,
            created_at=original_created_at or created_at_dt or _utcnow(),
        )

        if existing:
            repo.update(domain_acc)
        else:
            repo.create(domain_acc)
        repo.commit()

        logger.debug(f"Account {self.account_number} saved to database.")

    def log_transaction(self, txn_type, amount, description, target_acc=None, category=None):
        """Log a transaction — writes to SQLite only (no JSON)."""
        from datetime import datetime
        from decimal import Decimal
        from container import get_container
        from domain.entities import Transaction as DomainTransaction, TransactionType
        from sqlalchemy.exc import IntegrityError

        c = get_container()
        txn_id = generate_transaction_id()

        # Ensure the account row exists in SQLite first (in case it was only in JSON)
        acc_repo = c.account_repo()
        if not acc_repo.exists(self.account_number):
            from domain.entities import Account as DomainAccount
            acc_repo.create(DomainAccount(
                account_number=self.account_number,
                name=self.name,
                password=self.password,
                balance=Decimal(str(self.balance)),
                is_active=self.is_active,
                is_frozen=self.is_frozen,
            ))
            acc_repo.commit()

        domain_txn = DomainTransaction(
            txn_id=txn_id,
            account_number=self.account_number,
            type=TransactionType(txn_type.upper()),
            amount=Decimal(str(amount)),
            balance=Decimal(str(self.balance)),
            description=description,
            category=category or "General",
            target_account=target_acc,
        )
        try:
            c.transaction_repo().create(domain_txn)
            c.transaction_repo().commit()
        except IntegrityError:
            c.transaction_repo().rollback()
            logger.warning(
                f"Transaction logging skipped for {txn_id} "
                f"(account {self.account_number} may not exist)"
            )

        logger.info(
            f"TXN [{txn_id}]  {txn_type:<14}  Acc:{self.account_number}  "
            f"Amt:{fmt_currency(amount)}  Bal:{fmt_currency(self.balance)}"
            + (f"  -> {target_acc}" if target_acc else "")
        )
        return txn_id

    def check_balance(self):
        header("ACCOUNT BALANCE")
        print(f"  {GREEN}Account No : {BOLD}{self.account_number}{RESET}")
        print(f"  {GREEN}Name       : {BOLD}{self.name}{RESET}")
        print(f"  {GREEN}Balance    : {BOLD}{fmt_currency(self.balance)}{RESET}")
        divider()
        logger.info(f"Balance checked -> Acc:{self.account_number}  Bal:{fmt_currency(self.balance)}")

    def mini_statement(self):
        header("MINI STATEMENT  (Last 5 transactions)")
        txns    = load_json(TRANSACTIONS_FILE)
        records = txns.get(self.account_number, [])
        last5   = records[-5:]
        if not last5:
            info("No transactions found.")
        else:
            for t in reversed(last5):
                sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER_IN") else "-"
                color = GREEN if sign == "+" else RED
                cat = t.get("category", "")
                print(f"  {t['timestamp']}  |  {t['type']:<14}  |  "
                      f"{color}{sign}{fmt_currency(t['amount'])}{RESET}  |  Bal: {fmt_currency(t['balance'])}")
                if cat:
                    print(f"  {'':>12}[{cat}]")
        divider()
        logger.info(f"Mini statement viewed -> Acc:{self.account_number}")

    def full_statement(self):
        header("FULL TRANSACTION HISTORY")
        txns    = load_json(TRANSACTIONS_FILE)
        records = txns.get(self.account_number, [])
        if not records:
            info("No transactions found.")
        else:
            for t in records:
                sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER_IN") else "-"
                color = GREEN if sign == "+" else RED
                cat = t.get("category", "")
                print(f"  [{t['txn_id']}]  {t['timestamp']}  |  "
                      f"{t['type']:<14}  |  {color}{sign}{fmt_currency(t['amount'])}{RESET}  |  "
                      f"Bal: {fmt_currency(t['balance'])}")
                if cat and cat != "General":
                    print(f"    {CYAN}    Category: {cat}{RESET}")
                if t.get("description"):
                    print(f"    {CYAN}    Note: {t['description']}{RESET}")
        divider()
        logger.info(f"Full statement viewed -> Acc:{self.account_number}")

    def view_profile(self):
        status = "FROZEN" if self.is_frozen else ("ACTIVE" if self.is_active else "CLOSED")
        status_color = RED if self.is_frozen else (GREEN if self.is_active else YELLOW)
        header("PROFILE DETAILS")
        print(f"  {CYAN}Name           :{WHITE} {self.name}{RESET}")
        print(f"  {CYAN}Age            :{WHITE} {self.age}{RESET}")
        print(f"  {CYAN}Gender         :{WHITE} {self.gender}{RESET}")
        print(f"  {CYAN}Mobile         :{WHITE} {self.mobile}{RESET}")
        print(f"  {CYAN}Email          :{WHITE} {self.email}{RESET}")
        print(f"  {CYAN}Account Number :{WHITE} {self.account_number}{RESET}")
        print(f"  {CYAN}Balance        :{WHITE} {fmt_currency(self.balance)}{RESET}")
        print(f"  {CYAN}Account Status :{WHITE} {status_color}{status}{RESET}")
        print(f"  {CYAN}Member Since   :{WHITE} {self.created_at}{RESET}")
        divider()

    def deposit(self):
        header("DEPOSIT MONEY")
        amount = get_float("  Enter amount to deposit : Rs.")
        if amount is None:
            return
        category = get_category_choice()

        result = process_deposit(self.account_number, amount, category)
        if result.success:
            self.balance = result.data["balance"]
            success(result.message)
        else:
            error(result.message)
        divider()

    def withdraw(self):
        header("WITHDRAW MONEY")
        amount = get_float("  Enter amount to withdraw : Rs.")
        if amount is None:
            return
        category = get_category_choice()

        result = process_withdraw(self.account_number, amount, category)
        if result.success:
            self.balance = result.data["balance"]
            success(result.message)
        else:
            error(result.message)
        divider()

    def transfer_funds(self):
        """Transfer funds using an atomic SQLite transaction (via service layer)."""
        header("TRANSFER FUNDS")
        target_acc_no = input("  Enter recipient account number : ").strip()

        accounts = load_json(ACCOUNTS_FILE)
        if target_acc_no not in accounts:
            error("Recipient account not found.")
            divider()
            return
        if target_acc_no == self.account_number:
            error("Cannot transfer to your own account.")
            divider()
            return

        target_data = accounts[target_acc_no]
        if target_data.get("is_frozen"):
            error("Recipient account is frozen.")
            divider()
            return
        if not target_data.get("is_active", True):
            error("Recipient account is closed.")
            divider()
            return

        print(f"  {CYAN}Recipient : {BOLD}{target_data['name']}{RESET}")
        amount = get_float("  Enter amount to transfer : Rs.")
        if amount is None:
            return

        category = get_category_choice()
        confirm = input(f"  Confirm transfer of {YELLOW}{fmt_currency(amount)}{RESET} to {CYAN}{target_data['name']}{RESET}? (y/n): ")
        if confirm.lower() != "y":
            warning("Transfer cancelled.")
            divider()
            return

        result = process_transfer(
            sender_acc_no=self.account_number,
            receiver_acc_no=target_acc_no,
            amount=amount,
            category=category,
        )

        if result.success:
            self.balance = result.sender_balance
            success(f"{fmt_currency(amount)} transferred to {target_data['name']} successfully!")
            print(f"  {GREEN}Your New Balance : {BOLD}{fmt_currency(self.balance)}{RESET}")
        else:
            error(result.error_message)
        divider()

    def update_profile(self):
        header("UPDATE PROFILE")
        print(f"  {WHITE}(Press Enter to keep current value)\n{RESET}")
        name   = input(f"  Name   [{CYAN}{self.name}{RESET}]   : ").strip()
        age    = input(f"  Age    [{CYAN}{self.age}{RESET}]    : ").strip()
        gender = input(f"  Gender [{CYAN}{self.gender}{RESET}] : ").strip()
        mobile = input(f"  Mobile [{CYAN}{self.mobile}{RESET}] : ").strip()
        email  = input(f"  Email  [{CYAN}{self.email}{RESET}]  : ").strip()
        old_name = self.name
        if name:
            if not validate_name(name):
                error("Invalid name. Must be 2-50 characters (letters and spaces only).")
                return
            self.name = name
        if age:
            try:   self.age = int(age)
            except ValueError: error("Invalid age - keeping current.")
        if gender: self.gender = gender
        if mobile:
            if not validate_phone(mobile):
                error("Invalid mobile number. Must be 10 digits starting with 6-9.")
                return
            self.mobile = mobile
        if email:
            if not validate_email(email):
                error("Invalid email format.")
                return
            self.email = email
        self.save()
        logger.info(f"Profile updated -> Acc:{self.account_number}  (was: {old_name}  now: {self.name})")
        success("Profile updated successfully!")
        divider()

    def change_password(self):
        header("CHANGE PASSWORD")
        old_pwd = prompt_password("  Enter current password : ")
        if not verify_password(old_pwd, self.password):
            logger.warning(f"Failed password change attempt -> Acc:{self.account_number}")
            error("Incorrect current password.")
            divider()
            return
        new_pwd = prompt_password("  Enter new password     : ")
        valid_pwd, pwd_msg = validate_password(new_pwd)
        if not valid_pwd:
            error(pwd_msg)
            divider()
            return
        confirm = prompt_password("  Confirm new password   : ")
        if new_pwd != confirm:
            error("Passwords do not match.")
            divider()
            return
        self.password = hash_password(new_pwd)
        self.save()
        logger.info(f"Password changed -> Acc:{self.account_number}")
        success("Password changed successfully!")
        divider()

    def close_account(self):
        header("CLOSE ACCOUNT")
        print(f"  {RED}{BOLD}WARNING: This action is irreversible!{RESET}")
        confirm = input(f"  {YELLOW}Type 'CLOSE' to confirm :{RESET} ").strip()
        if confirm != "CLOSE":
            warning("Cancelled.")
            divider()
            return
        pwd = prompt_password("  Enter password to confirm : ")

        result = process_close_account(self.account_number, pwd, self.password)
        if result.success:
            self.is_active = False
            print(f"  {RED}{BOLD}{result.message} Goodbye!{RESET}")
        else:
            error(result.message)
        divider()

    def export_csv(self):
        """Export full transaction history to CSV."""
        header("EXPORT TO CSV")
        txns = load_json(TRANSACTIONS_FILE)
        records = txns.get(self.account_number, [])
        if not records:
            info("No transactions to export.")
            divider()
            return
        filename = generate_csv_filename(self.account_number)
        export_transactions_to_csv(self.account_number, records, filename)
        success(f"Statement exported to: {filename}")
        logger.info(f"CSV exported -> Acc:{self.account_number}  File:{filename}")
        divider()

    def _show_goal(self, goal: dict, index: int):
        """Display a single savings goal."""
        pct = (goal["current_amount"] / goal["target_amount"] * 100) if goal["target_amount"] > 0 else 0
        status = "✅ COMPLETED" if goal.get("is_completed") else "🔄 ACTIVE"
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  {index}. {goal['name']}")
        print(f"     {status}  |  {fmt_currency(goal['current_amount'])} / {fmt_currency(goal['target_amount'])}  ({pct:.1f}%)")
        print(f"     [{bar}]")
        if goal.get("target_date"):
            print(f"     Target date: {goal['target_date']}")
        print()

    def savings_goals_menu(self):
        """Savings goals management menu."""
        while True:
            goals = load_goals(self.account_number)
            header("🎯 SAVINGS GOALS")
            if goals:
                total_saved = sum(g["current_amount"] for g in goals)
                completed = sum(1 for g in goals if g.get("is_completed"))
                print(f"  Goals: {len(goals)}  |  Completed: {completed}  |  Total saved: {fmt_currency(total_saved)}")
                print()
                for i, g in enumerate(goals, 1):
                    self._show_goal(g, i)
            else:
                info("No savings goals yet. Create one below!")
                print()

            print(f"  {CYAN}{'─' * 42}{RESET}")
            print(f"  {WHITE}  1) Create New Goal{RESET}")
            print(f"  {WHITE}  2) Contribute to Goal{RESET}")
            print(f"  {WHITE}  3) Edit Goal{RESET}")
            print(f"  {WHITE}  4) Delete Goal{RESET}")
            print(f"  {WHITE}  5) Back to Account Services{RESET}")
            print(f"  {CYAN}{'─' * 42}{RESET}")

            choice = input("  Enter choice: ").strip()

            if choice == "1":
                self._create_goal()
            elif choice == "2":
                self._contribute_to_goal()
            elif choice == "3":
                self._edit_goal()
            elif choice == "4":
                self._delete_goal()
            elif choice == "5":
                break
            else:
                error("Invalid choice.")

    def _create_goal(self):
        header("🎯 CREATE SAVINGS GOAL")
        name = input("  Goal name: ").strip()
        if not name or len(name) < 2:
            error("Goal name must be at least 2 characters.")
            return
        target = get_float("  Target amount: Rs.")
        if target is None:
            return
        date_str = input("  Target date (YYYY-MM-DD, optional): ").strip()

        goals = load_goals(self.account_number)
        goal = {
            "goal_id": generate_goal_id(),
            "name": name,
            "target_amount": round(target, 2),
            "current_amount": 0.0,
            "target_date": date_str,
            "created_at": now_str(),
            "is_completed": False,
        }
        goals.append(goal)
        save_goals(self.account_number, goals)
        logger.info(f"Savings goal created -> Acc:{self.account_number}  Goal:{name}")
        success(f"Goal '{name}' created!")
        divider()

    def _contribute_to_goal(self):
        goals = load_goals(self.account_number)
        active = [g for g in goals if not g.get("is_completed")]
        if not active:
            error("No active goals to contribute to.")
            return

        header("💰 CONTRIBUTE TO GOAL")
        for i, g in enumerate(active, 1):
            print(f"  {i}. {g['name']} — {fmt_currency(g['current_amount'])} / {fmt_currency(g['target_amount'])}")
        print()
        idx = get_int("  Select goal number: ")
        if idx is None or idx < 1 or idx > len(active):
            error("Invalid selection.")
            return
        goal = active[idx - 1]

        amount = get_float(f"  Amount to contribute to '{goal['name']}': Rs.")
        if amount is None:
            return

        confirm = input(f"  Contribute {YELLOW}{fmt_currency(amount)}{RESET} to '{goal['name']}'? (y/n): ").strip().lower()
        if confirm != "y":
            warning("Cancelled.")
            return

        result = contribute_to_goal(self.account_number, goal["goal_id"], amount, self.balance)
        if result.success:
            # Service already deducted from JSON; update in-memory balance
            self.balance -= amount
            success(result.message)
        else:
            error(result.message)
        print(f"  {GREEN}New Balance: {BOLD}{fmt_currency(self.balance)}{RESET}")
        divider()

    def _edit_goal(self):
        goals = load_goals(self.account_number)
        if not goals:
            error("No goals to edit.")
            return

        header("✏️ EDIT GOAL")
        for i, g in enumerate(goals, 1):
            print(f"  {i}. {g['name']} — {fmt_currency(g['current_amount'])} / {fmt_currency(g['target_amount'])}")
        print()
        idx = get_int("  Select goal number: ")
        if idx is None or idx < 1 or idx > len(goals):
            error("Invalid selection.")
            return
        goal = goals[idx - 1]

        name = input(f"  Name [{goal['name']}]: ").strip()
        if name:
            goal['name'] = name
        target_str = input(f"  Target amount [{goal['target_amount']}]: ").strip()
        if target_str:
            try:
                goal['target_amount'] = round(float(target_str), 2)
            except ValueError:
                error("Invalid amount.")
                return
        date_str = input(f"  Target date [{goal.get('target_date', '') or 'None'}]: ").strip()
        goal['target_date'] = date_str
        goal['is_completed'] = goal['current_amount'] >= goal['target_amount']

        save_goals(self.account_number, goals)
        logger.info(f"Goal edited -> Acc:{self.account_number}  Goal:{goal['name']}")
        success("Goal updated!")
        divider()

    def _delete_goal(self):
        goals = load_goals(self.account_number)
        if not goals:
            error("No goals to delete.")
            return

        header("🗑️ DELETE GOAL")
        for i, g in enumerate(goals, 1):
            print(f"  {i}. {g['name']} — {fmt_currency(g['current_amount'])} / {fmt_currency(g['target_amount'])}")
        print()
        idx = get_int("  Select goal number: ")
        if idx is None or idx < 1 or idx > len(goals):
            error("Invalid selection.")
            return
        goal = goals[idx - 1]

        confirm = input(f"  Delete '{goal['name']}'? Amount will be refunded. (y/n): ").strip().lower()
        if confirm != "y":
            warning("Cancelled.")
            return

        result = delete_savings_goal(self.account_number, goal["goal_id"])
        if result.success:
            if goal["current_amount"] > 0:
                self.balance += goal["current_amount"]
            success(result.message)
        else:
            error(result.message)
        divider()

    def apply_interest(self):
        """Apply monthly interest using an atomic SQLite transaction."""
        header("INTEREST CALCULATION")
        result = process_apply_interest(self.account_number, self.balance)
        if result.success:
            self.balance = result.data["balance"]
            success(result.message)
        else:
            if "No interest" in result.message:
                info(result.message)
            else:
                error(result.message)
        divider()
