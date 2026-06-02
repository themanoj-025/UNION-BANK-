"""
main.py - Entry point for Union Bank Management System
"""

import os
import sys

# Ensure project directory is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from bank import Bank
from admin import Admin
from logger import logger
from utils import load_json, save_json, ACCOUNTS_FILE, TRANSACTIONS_FILE
from ui import header, divider, success, error, info, GREEN, CYAN, WHITE, YELLOW, BOLD, RESET


# Initialize data files if they do not exist
def init_files():
    if not os.path.exists(ACCOUNTS_FILE):
        save_json(ACCOUNTS_FILE, {})
    if not os.path.exists(TRANSACTIONS_FILE):
        save_json(TRANSACTIONS_FILE, {})


def main_menu():
    bank = Bank()
    admin = Admin()

    logger.info("=== Union Bank System Started ===")

    while True:
        print(f"""
  {GREEN}{'╔' + '═' * 46 + '╗'}{RESET}
  {GREEN}║{RESET}  {YELLOW}{BOLD}       UNION BANK MANAGEMENT SYSTEM       {RESET}{GREEN}║{RESET}
  {GREEN}{'╠' + '═' * 46 + '╣'}{RESET}
  {GREEN}║{RESET}  {CYAN}   1)  Register New Account{RESET}                {GREEN}║{RESET}
  {GREEN}║{RESET}  {CYAN}   2)  Customer Login{RESET}                     {GREEN}║{RESET}
  {GREEN}║{RESET}  {CYAN}   3)  Admin Login{RESET}                         {GREEN}║{RESET}
  {GREEN}║{RESET}  {CYAN}   4)  Exit{RESET}                                {GREEN}║{RESET}
  {GREEN}{'╚' + '═' * 46 + '╝'}{RESET}
""")

        choice = input(f"  {YELLOW}Enter choice:{RESET} ").strip()

        try:
            if choice == "1":
                bank.register()

            elif choice == "2":
                bank.login()

            elif choice == "3":
                admin.login()

            elif choice == "4":
                logger.info("=== Union Bank System Shutdown ===")
                print(f"\n  {GREEN}Thank you for banking with Union Bank. Goodbye!{RESET}\n")
                break

            else:
                error("Invalid choice. Please enter 1-4.")

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            error("Something went wrong. Please try again.")


if __name__ == "__main__":
    init_files()
    main_menu()