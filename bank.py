"""
bank.py  -  Bank class: registration, login, all menu loops (with logging).
"""

import time as _time

from account import Account
from utils import (
    load_json, save_json,
    generate_account_number,
    now_str, fmt_currency,
    hash_password, verify_password,
    validate_email, validate_phone, validate_password, validate_name,
    check_login_locked, record_failed_login, reset_login_attempts,
    check_session_timeout, get_session_timeout_seconds,
    LOGIN_LOCKOUT_MINUTES,
    ACCOUNTS_FILE,
)
from ui import (
    header, divider, success, error, warning, info,
    prompt_password, GREEN, CYAN, WHITE, YELLOW, BOLD, RESET, clear_screen,
)
from logger import logger


class Bank:

    def register(self):
        header("NEW ACCOUNT REGISTRATION")

        name = input("  Full Name      : ").strip()
        if not validate_name(name):
            error("Name must be 2-50 characters (letters and spaces only).")
            return

        age_str = input("  Age            : ").strip()
        try:
            age = int(age_str)
            if age < 18:
                error("You must be at least 18 to open an account.")
                return
            if age > 120:
                error("Please enter a valid age.")
                return
        except ValueError:
            error("Invalid age.")
            return

        gender  = input("  Gender         : ").strip()

        mobile  = input("  Mobile Number  : ").strip()
        if not validate_phone(mobile):
            error("Invalid mobile number. Must be 10 digits starting with 6-9.")
            return

        email   = input("  Email Address  : ").strip()
        if not validate_email(email):
            error("Invalid email format.")
            return

        pwd     = prompt_password("  Create Password: ")
        valid_pwd, pwd_msg = validate_password(pwd)
        if not valid_pwd:
            error(pwd_msg)
            return

        confirm = prompt_password("  Confirm Password: ")

        if pwd != confirm:
            error("Passwords do not match.")
            return

        acc_no = generate_account_number()
        data = {
            "account_number": acc_no,
            "name":      name,
            "age":       age,
            "gender":    gender,
            "mobile":    mobile,
            "email":     email,
            "password":  hash_password(pwd),
            "balance":   0.0,
            "is_active": True,
            "is_frozen": False,
            "created_at": now_str(),
        }

        account = Account(data)
        account.save()

        logger.info(f"New account registered -> Acc:{acc_no}  Name:{name}")

        divider()
        success("Registration Successful!")
        print(f"\n  Name           : {name}")
        print(f"  Account Number : {acc_no}")
        print(f"  Balance        : {fmt_currency(0)}")
        print(f"  Date           : {data['created_at']}")
        divider()
        print("  Please keep your account number safe.\n")

    def login(self):
        header("ACCOUNT LOGIN")
        acc_no = input("  Account Number : ").strip()

        # Check rate limiting
        is_locked, remaining = check_login_locked(acc_no)
        if is_locked:
            logger.warning(f"Login blocked - account locked: {acc_no}")
            error(f"Account locked due to too many failed attempts. Try again in {remaining} minute(s).")
            divider()
            return

        pwd    = prompt_password("  Password       : ")

        accounts = load_json(ACCOUNTS_FILE)
        if acc_no not in accounts:
            logger.warning(f"Login failed - account not found: {acc_no}")
            error("Account not found.")
            divider()
            return

        data = accounts[acc_no]

        if data.get("is_frozen", False):
            logger.warning(f"Login blocked - account frozen: {acc_no}")
            error("Your account has been frozen. Please contact the bank.")
            divider()
            return

        if not data.get("is_active", True):
            logger.warning(f"Login blocked - account closed: {acc_no}")
            error("This account has been closed.")
            divider()
            return

        if not verify_password(pwd, data["password"]):
            logger.warning(f"Login failed - wrong password: Acc:{acc_no}")
            remaining_attempts = record_failed_login(acc_no)
            if remaining_attempts > 0:
                error(f"Incorrect password. {remaining_attempts} attempt(s) remaining before lockout.")
            else:
                error(f"Incorrect password. Account locked for {LOGIN_LOCKOUT_MINUTES} minutes.")
            divider()
            return

        # Successful login — reset attempts
        reset_login_attempts(acc_no)
        logger.info(f"Login successful -> Acc:{acc_no}  Name:{data['name']}")
        success(f"Welcome back, {data['name']}!")
        divider()
        account = Account(data)
        account.last_activity = _time.time()
        self._dashboard(account)

    def _dashboard(self, acc):
        acc.last_activity = _time.time()

        while True:
            # Check session timeout
            if not check_session_timeout(acc.last_activity):
                mins = get_session_timeout_seconds() // 60
                warning(f"Session timed out after {mins} minutes of inactivity. Please login again.")
                logger.info(f"Session timeout -> Acc:{acc.account_number}  Name:{acc.name}")
                break

            accounts = load_json(ACCOUNTS_FILE)
            fresh = accounts.get(acc.account_number)
            if fresh:
                acc.balance   = fresh["balance"]
                acc.is_active = fresh.get("is_active", True)
                acc.is_frozen = fresh.get("is_frozen", False)

            if acc.is_frozen:
                error("Your account has been frozen by admin. Logging out.")
                logger.warning(f"Session terminated - account frozen mid-session: Acc:{acc.account_number}")
                break
            if not acc.is_active:
                warning("Account closed. Logging out.")
                break

            print(f"""
  {GREEN}{BOLD}{'═' * 50}{RESET}
  {GREEN}   Welcome, {acc.name}{RESET}
  {GREEN}   Account No : {acc.account_number}{RESET}
  {GREEN}   Balance    : {fmt_currency(acc.balance)}{RESET}
  {YELLOW}   (Session: active){RESET}
  {GREEN}{'═' * 50}{RESET}
  {CYAN}   1) Account Services{RESET}
  {CYAN}   2) Transactions{RESET}
  {CYAN}   3) Profile Settings{RESET}
  {CYAN}   4) Logout{RESET}
  {GREEN}{'═' * 50}{RESET}""")

            choice = input("  Enter choice: ").strip()
            acc.last_activity = _time.time()  # Reset timer on any interaction

            if choice == "1":
                self._account_services(acc)
            elif choice == "2":
                self._transactions_menu(acc)
            elif choice == "3":
                self._profile_settings(acc)
            elif choice == "4":
                logger.info(f"Logout -> Acc:{acc.account_number}  Name:{acc.name}")
                print("  Logging out... Goodbye!\n")
                break
            else:
                error("Invalid choice. Please try again.")

    def _account_services(self, acc):
        while True:
            print(f"""
  {CYAN}{'─' * 42}{RESET}
  {CYAN}{BOLD}   ACCOUNT SERVICES{RESET}
  {CYAN}{'─' * 42}{RESET}
  {WHITE}   1) Check Balance{RESET}
  {WHITE}   2) Mini Statement  (last 5 txns){RESET}
  {WHITE}   3) Full Statement{RESET}
  {WHITE}   4) View Profile{RESET}          {WHITE}   5) Export Statement to CSV{RESET}
  {WHITE}   6) Apply Monthly Interest{RESET}
  {WHITE}   7) Savings Goals{RESET}
  {WHITE}   8) Back{RESET}
  {CYAN}{'─' * 42}{RESET}""")
            choice = input("  Enter choice: ").strip()
            if choice == "1":
                acc.check_balance()
            elif choice == "2":
                acc.mini_statement()
            elif choice == "3":
                acc.full_statement()
            elif choice == "4":
                acc.view_profile()
            elif choice == "5":
                acc.export_csv()
            elif choice == "6":
                acc.apply_interest()
            elif choice == "7":
                acc.savings_goals_menu()
            elif choice == "8":
                break
            else:
                error("Invalid choice.")

    def _transactions_menu(self, acc):
        while True:
            print(f"""
  {CYAN}{'─' * 42}{RESET}
  {CYAN}{BOLD}   TRANSACTIONS{RESET}
  {CYAN}{'─' * 42}{RESET}
  {WHITE}   1) Deposit Money{RESET}
  {WHITE}   2) Withdraw Money{RESET}
  {WHITE}   3) Transfer Funds{RESET}
  {WHITE}   4) Back{RESET}
  {CYAN}{'─' * 42}{RESET}""")
            choice = input("  Enter choice: ").strip()
            if choice == "1":
                acc.deposit()
            elif choice == "2":
                acc.withdraw()
            elif choice == "3":
                acc.transfer_funds()
            elif choice == "4":
                break
            else:
                error("Invalid choice.")

    def _profile_settings(self, acc):
        while True:
            print(f"""
  {CYAN}{'─' * 42}{RESET}
  {CYAN}{BOLD}   PROFILE SETTINGS{RESET}
  {CYAN}{'─' * 42}{RESET}
  {WHITE}   1) Update Profile{RESET}
  {WHITE}   2) Change Password{RESET}
  {WHITE}   3) Close Account{RESET}
  {WHITE}   4) Back{RESET}
  {CYAN}{'─' * 42}{RESET}""")
            choice = input("  Enter choice: ").strip()
            if choice == "1":
                acc.update_profile()
            elif choice == "2":
                acc.change_password()
            elif choice == "3":
                acc.close_account()
                if not acc.is_active:
                    return
            elif choice == "4":
                break
            else:
                error("Invalid choice.")
