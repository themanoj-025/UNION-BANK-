"""
main.py - Entry point for Union Bank Management System

Boot sequence:
  1. SQLite database (init_db)
  2. DI Container (repositories, services)
  3. CLI interface (Bank, Admin)

No JSON files are created or used at startup.
Fresh installations automatically initialize the database via init_db().
"""

import os
import sys

# Ensure project directory is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Ensure src/ directory is on the path so all imports resolve correctly
_SRC_DIR = os.path.join(BASE_DIR, 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from bank import Bank
from admin import Admin
from logger import logger
from ui import header, divider, success, error, info, GREEN, CYAN, WHITE, YELLOW, BOLD, RESET


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


def create_admin_bootstrap():
    """CLI command: create the initial admin user with a strong password.

    Usage: python main.py create-admin

    Prompts for a username and a strong password (min 12 chars),
    then creates the admin user in the database. Fails if an admin
    already exists (they must use 'change-admin-password' instead).
    """
    import getpass
    from container import get_container, init_db
    from domain.entities import AdminUser
    from utils import hash_password, validate_password

    init_db()
    c = get_container()

    # Check if any admin already exists
    existing_count = c.admin_repo().admin_count()
    if existing_count > 0:
        print("\n  [!] An admin user already exists.")
        print("  Use 'change-admin-password' via the admin panel instead.\n")
        sys.exit(1)

    print(f"\n  {'─' * 40}")
    print("  CREATE INITIAL ADMIN USER")
    print(f"  {'─' * 40}")

    username = input("  Username: ").strip()
    if not username or len(username) < 3:
        print("  [!] Username must be at least 3 characters.\n")
        sys.exit(1)

    password = getpass.getpass("  Password: ")
    confirm = getpass.getpass("  Confirm: ")

    if password != confirm:
        print("  [!] Passwords do not match.\n")
        sys.exit(1)

    valid, msg = validate_password(password)
    if not valid:
        print(f"  [!] {msg}\n")
        sys.exit(1)

    admin = AdminUser(
        username=username,
        password=hash_password(password),
        role="admin",
    )
    c.admin_repo().create(admin)
    c.admin_repo().commit()

    print(f"\n  [+] Admin user '{username}' created successfully!\n")
    print(f"  You can now log in via the admin panel.\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        create_admin_bootstrap()
    else:
        # Database auto-initializes on first container request
        main_menu()