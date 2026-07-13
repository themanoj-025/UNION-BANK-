"""
admin.py  –  Admin Panel for Union Bank Management System.

Admin credentials are stored in data/admin.json.
Default → username: simon | password: simon123
"""

import os
from utils import (
    load_json, save_json,
    now_str, fmt_currency,
    hash_password, verify_password, validate_password,
    check_login_locked, record_failed_login, reset_login_attempts,
    LOGIN_LOCKOUT_MINUTES,
    ACCOUNTS_FILE, TRANSACTIONS_FILE, ADMIN_FILE,
)
from ui import header, divider, success, error, warning, info, prompt_password, GREEN, RED, CYAN, WHITE, YELLOW, BOLD, RESET
from logger import logger
from services import get_bank_statistics, process_freeze_account, process_delete_account


# ─────────────────────────────────────────────────────────────────────────────
#  Bootstrap default admin credentials
# ─────────────────────────────────────────────────────────────────────────────

def _init_admin():
    if not os.path.exists(ADMIN_FILE):
        save_json(ADMIN_FILE, {
            "username": "simon",
            "password": hash_password("simon123"),
        })
    else:
        creds = load_json(ADMIN_FILE)
        stored_pwd = creds.get("password", "")
        if stored_pwd and not stored_pwd.startswith("$2"):
            logger.info("Migrating plain-text admin password to bcrypt hash.")
            creds["password"] = hash_password(stored_pwd)
            save_json(ADMIN_FILE, creds)

_init_admin()


class Admin:

    def login(self):
        header("ADMIN LOGIN")
        creds = load_json(ADMIN_FILE)
        username = input("  Username : ").strip()
        password = prompt_password("  Password : ")

        # Check rate limiting for admin
        lock_key = f"admin_{username}"
        is_locked, remaining = check_login_locked(lock_key)
        if is_locked:
            logger.warning(f"Admin login blocked - locked: {username}")
            error(f"Admin account locked due to too many failed attempts. Try again in {remaining} minute(s).")
            divider()
            return

        if username == creds["username"] and verify_password(password, creds["password"]):
            reset_login_attempts(lock_key)
            logger.info(f"Admin login successful → '{username}'")
            success("Admin login successful!")
            print()
            self._admin_dashboard()
        else:
            logger.warning(f"Failed admin login attempt → username='{username}'")
            remaining_attempts = record_failed_login(lock_key)
            if remaining_attempts > 0:
                error(f"Invalid admin credentials. {remaining_attempts} attempt(s) remaining before lockout.")
            else:
                error(f"Invalid admin credentials. Admin account locked for {LOGIN_LOCKOUT_MINUTES} minutes.")
            divider()

    # ── dashboard ─────────────────────────────────────────────────────────────

    def _admin_dashboard(self):
        while True:
            print("""
  ╔══════════════════════════════════════════╗
  ║           ADMIN CONTROL PANEL            ║
  ╠══════════════════════════════════════════╣
  ║  1)  View All Accounts                   ║
  ║  2)  Search Account                      ║
  ║  3)  Freeze / Unfreeze Account           ║
  ║  4)  Delete Account                      ║
  ║  5)  Bank Statistics                     ║
  ║  6)  View All Transactions               ║
  ║  7)  Change Admin Password               ║
  ║  8)  Logout                              ║
  ╚══════════════════════════════════════════╝""")
            choice = input("  Enter choice: ").strip()

            if   choice == "1": self._view_all_accounts()
            elif choice == "2": self._search_account()
            elif choice == "3": self._freeze_account()
            elif choice == "4": self._delete_account()
            elif choice == "5": self._bank_statistics()
            elif choice == "6": self._view_all_transactions()
            elif choice == "7": self._change_admin_password()
            elif choice == "8":
                logger.info("Admin logged out.")
                print("  Admin logged out.\n")
                break
            else:
                error("Invalid choice.")

    # ── 1. view all accounts ──────────────────────────────────────────────────

    def _view_all_accounts(self):
        header("ALL ACCOUNTS")
        accounts = load_json(ACCOUNTS_FILE)
        if not accounts:
            info("No accounts found.")
            divider()
            return

        print(f"  {BOLD}{'ACC NUMBER':<14} {'NAME':<20} {'BALANCE':>12}  {'STATUS':<10}  CREATED{RESET}")
        print(f"  {CYAN}{"-" * 72}{RESET}")
        for acc in accounts.values():
            if acc.get("is_frozen", False):
                status_color = RED
                status = "FROZEN"
            elif not acc.get("is_active", True):
                status_color = YELLOW
                status = "CLOSED"
            else:
                status_color = GREEN
                status = "ACTIVE"
            print(f"  {acc['account_number']:<14} {acc['name']:<20} "
                  f"{fmt_currency(acc['balance']):>12}  {status_color}{status:<13}{RESET}  {acc.get('created_at','N/A')}")
        divider()

    # ── 2. search account ────────────────────────────────────────────────────

    def _search_account(self):
        header("SEARCH ACCOUNT")
        query = input("  Enter Account Number or Name : ").strip().lower()
        accounts = load_json(ACCOUNTS_FILE)
        results = [
            a for a in accounts.values()
            if query in a["account_number"].lower() or query in a["name"].lower()
        ]
        if not results:
            info("No matching accounts found.")
        else:
            for a in results:
                if a.get("is_frozen"):
                    status_color = RED
                    status = "FROZEN"
                elif a.get("is_active", True):
                    status_color = GREEN
                    status = "ACTIVE"
                else:
                    status_color = YELLOW
                    status = "CLOSED"
                print(f"""
  {CYAN}{'─' * 40}{RESET}
  {CYAN}Account No :{WHITE} {a['account_number']}{RESET}
  {CYAN}Name       :{WHITE} {a['name']}{RESET}
  {CYAN}Age        :{WHITE} {a['age']}{RESET}
  {CYAN}Mobile     :{WHITE} {a['mobile']}{RESET}
  {CYAN}Email      :{WHITE} {a['email']}{RESET}
  {CYAN}Balance    :{WHITE} {fmt_currency(a['balance'])}{RESET}
  {CYAN}Status     :{WHITE} {status_color}{status}{RESET}
  {CYAN}Created    :{WHITE} {a.get('created_at','N/A')}{RESET}
  {CYAN}{'─' * 40}{RESET}""")
        divider()

    # ── 3. freeze / unfreeze ─────────────────────────────────────────────────

    def _freeze_account(self):
        header("FREEZE / UNFREEZE ACCOUNT")
        acc_no = input("  Enter Account Number : ").strip()
        accounts = load_json(ACCOUNTS_FILE)

        if acc_no not in accounts:
            error("Account not found.")
            divider()
            return

        acc = accounts[acc_no]
        if not acc.get("is_active", True) and not acc.get("is_frozen", False):
            error("Account is permanently closed – cannot modify.")
            divider()
            return

        currently_frozen = acc.get("is_frozen", False)
        action = "UNFREEZE" if currently_frozen else "FREEZE"
        action_color = GREEN if currently_frozen else RED
        confirm = input(f"  {action_color}{action}{RESET} account of {CYAN}{acc['name']}{RESET}? (y/n): ").strip().lower()
        if confirm != "y":
            warning("Cancelled.")
            divider()
            return

        if currently_frozen:
            result = process_unfreeze_account(acc_no)
        else:
            result = process_freeze_account(acc_no)

        if result.success:
            success(result.message)
        else:
            error(result.message)
        divider()

    # ── 4. delete account ────────────────────────────────────────────────────

    def _delete_account(self):
        header("DELETE ACCOUNT")
        acc_no = input("  Enter Account Number to delete : ").strip()
        accounts = load_json(ACCOUNTS_FILE)

        if acc_no not in accounts:
            print("  [!] Account not found.")
            divider()
            return

        acc = accounts[acc_no]
        print(f"\n  {CYAN}Account   :{WHITE} {acc_no}{RESET}")
        print(f"  {CYAN}Name      :{WHITE} {acc['name']}{RESET}")
        print(f"  {CYAN}Balance   :{WHITE} {fmt_currency(acc['balance'])}{RESET}")
        print(f"\n  {RED}{BOLD}⚠  WARNING: This will permanently delete ALL data for this account!{RESET}")
        confirm = input(f"  {YELLOW}Type 'DELETE' to confirm :{RESET} ").strip()
        if confirm != "DELETE":
            warning("Cancelled.")
            divider()
            return

        result = process_delete_account(acc_no)
        if result.success:
            success(result.message)
        else:
            error(result.message)
        divider()

    # ── 5. bank statistics ────────────────────────────────────────────────────

    def _bank_statistics(self):
        header("BANK STATISTICS")
        s = get_bank_statistics()

        print(f"""
  {GREEN}{'┌' + '─' * 41 + '┐'}{RESET}
  {GREEN}│{RESET}  {BOLD}CUSTOMER STATISTICS{RESET}{' ' * 19}{GREEN}│{RESET}
  {GREEN}{'├' + '─' * 41 + '┤'}{RESET}
  {GREEN}│{RESET}  Total Customers   : {CYAN}{s['total_customers']:<5}{RESET}                {GREEN}│{RESET}
  {GREEN}│{RESET}  Active Accounts   : {GREEN}{s['active']:<5}{RESET}                {GREEN}│{RESET}
  {GREEN}│{RESET}  Frozen Accounts   : {RED}{s['frozen']:<5}{RESET}                {GREEN}│{RESET}
  {GREEN}│{RESET}  Closed Accounts   : {YELLOW}{s['closed']:<5}{RESET}                {GREEN}│{RESET}
  {GREEN}{'├' + '─' * 41 + '┤'}{RESET}
  {GREEN}│{RESET}  {BOLD}FINANCIAL SUMMARY{RESET}{' ' * 21}{GREEN}│{RESET}
  {GREEN}{'├' + '─' * 41 + '┤'}{RESET}
  {GREEN}│{RESET}  Total Bank Balance: {WHITE}{fmt_currency(s['total_balance']):<20}{RESET} {GREEN}│{RESET}
  {GREEN}│{RESET}  Total Deposits    : {WHITE}{fmt_currency(s['total_dep']):<20}{RESET} {GREEN}│{RESET}
  {GREEN}│{RESET}  Total Withdrawals : {WHITE}{fmt_currency(s['total_with']):<20}{RESET} {GREEN}│{RESET}
  {GREEN}│{RESET}  Total Transfers   : {WHITE}{fmt_currency(s['total_trans']):<20}{RESET} {GREEN}│{RESET}
  {GREEN}{'├' + '─' * 41 + '┤'}{RESET}
  {GREEN}│{RESET}  Total Transactions: {CYAN}{s['total_txns']:<5}{RESET}                {GREEN}│{RESET}
  {GREEN}{'└' + '─' * 41 + '┘'}{RESET}""")
        divider()

    # ── 6. view all transactions ─────────────────────────────────────────────

    def _view_all_transactions(self):
        header("ALL TRANSACTIONS")
        txns = load_json(TRANSACTIONS_FILE)
        if not txns:
            print("  No transactions recorded yet.")
            divider()
            return

        acc_filter = input(f"  {CYAN}Filter by Account Number (or press Enter to show all):{RESET} ").strip()

        count = 0
        for acc_no, records in txns.items():
            if acc_filter and acc_no != acc_filter:
                continue
            print(f"\n  {GREEN}Account: {BOLD}{acc_no}{RESET}")
            print(f"  {CYAN}{"-" * 70}{RESET}")
            for t in records:
                sign = "+" if t["type"] in ("DEPOSIT", "TRANSFER_IN") else "-"
                amt_color = GREEN if sign == "+" else RED
                print(f"  [{t['txn_id']}]  {t['timestamp']}  "
                      f"{t['type']:<14}  {amt_color}{sign}{fmt_currency(t['amount'])}{RESET}  "
                      f"Bal: {fmt_currency(t['balance'])}")
                count += 1

        print(f"\n  {WHITE}Total records shown: {BOLD}{count}{RESET}")
        divider()

    # ── 7. change admin password ─────────────────────────────────────────────

    def _change_admin_password(self):
        header("CHANGE ADMIN PASSWORD")
        creds = load_json(ADMIN_FILE)
        old = prompt_password("  Current Password : ")
        if not verify_password(old, creds["password"]):
            logger.warning("Admin password change failed – wrong current password.")
            error("Incorrect current password.")
            divider()
            return
        new = prompt_password("  New Password     : ")
        valid_pwd, pwd_msg = validate_password(new)
        if not valid_pwd:
            error(pwd_msg)
            divider()
            return
        confirm = prompt_password("  Confirm Password : ")
        if new != confirm:
            error("Passwords do not match.")
            divider()
            return
        creds["password"] = hash_password(new)
        save_json(ADMIN_FILE, creds)
        logger.info("Admin password changed successfully.")
        success("Admin password updated successfully!")
        divider()
