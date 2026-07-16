"""admin.py  –  Admin Panel for Union Bank Management System.

All operations use the DI container (repositories/services) — no direct JSON.
Admin accounts are created via the bootstrap CLI command:
    python main.py create-admin
"""

from logger import logger
from ui import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    WHITE,
    YELLOW,
    divider,
    error,
    header,
    info,
    prompt_password,
    success,
    warning,
)
from utils import (
    fmt_currency,
    hash_password,
    now_str,
    validate_password,
    verify_password,
)


class Admin:

    def login(self):
        header("ADMIN LOGIN")
        username = input("  Username : ").strip()
        password = prompt_password("  Password : ")

        from container import get_container
        c = get_container()

        # Use container's auth service for DB-backed admin login
        auth_result = c.auth_service().admin_login(username, password)

        if auth_result.success:
            logger.info(f"Admin login successful → '{username}'")
            success("Admin login successful!")
            print()
            self._admin_dashboard()
        else:
            msg = auth_result.message
            if "locked" in msg.lower():
                logger.warning(f"Admin login blocked - locked: {username}")
                error(msg)
            else:
                logger.warning(f"Failed admin login attempt → username='{username}'")
                error(msg)
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
  ║  7)  Loan Management                     ║
  ║  8)  Change Admin Password               ║
  ║  9)  Logout                              ║
  ╚══════════════════════════════════════════╝""")
            choice = input("  Enter choice: ").strip()

            if   choice == "1": self._view_all_accounts()
            elif choice == "2": self._search_account()
            elif choice == "3": self._freeze_account()
            elif choice == "4": self._delete_account()
            elif choice == "5": self._bank_statistics()
            elif choice == "6": self._view_all_transactions()
            elif choice == "7": self._loan_management()
            elif choice == "8": self._change_admin_password()
            elif choice == "9":
                logger.info("Admin logged out.")
                print("  Admin logged out.\n")
                break
            else:
                error("Invalid choice.")

    # ── Helper: get an account dict from SQLite via container ─────────────────

    def _get_account_dict(self, acc_no: str) -> dict | None:
        from container import get_container
        c = get_container()
        domain = c.account_repo().get(acc_no)
        if domain is None:
            return None
        return {
            "account_number": domain.account_number,
            "name": domain.name,
            "age": domain.age,
            "gender": domain.gender,
            "mobile": domain.mobile,
            "email": domain.email,
            "balance": float(domain.balance),
            "is_active": domain.is_active,
            "is_frozen": domain.is_frozen,
            "created_at": str(domain.created_at)[:19],
        }

    # ── 1. view all accounts ──────────────────────────────────────────────────

    def _view_all_accounts(self):
        header("ALL ACCOUNTS")
        from container import get_container
        c = get_container()
        domain_accounts = c.admin_service().list_accounts()

        if not domain_accounts:
            info("No accounts found.")
            divider()
            return

        print(f"  {BOLD}{'ACC NUMBER':<14} {'NAME':<20} {'BALANCE':>12}  {'STATUS':<10}  CREATED{RESET}")
        print(f"  {CYAN}{"-" * 72}{RESET}")
        for a in domain_accounts:
            if a.is_frozen:
                status_color = RED
                status = "FROZEN"
            elif not a.is_active:
                status_color = YELLOW
                status = "CLOSED"
            else:
                status_color = GREEN
                status = "ACTIVE"
            print(f"  {a.account_number:<14} {a.name:<20} "
                  f"{fmt_currency(float(a.balance)):>12}  {status_color}{status:<13}{RESET}  {str(a.created_at)[:19]}")
        divider()

    # ── 2. search account ────────────────────────────────────────────────────

    def _search_account(self):
        header("SEARCH ACCOUNT")
        query = input("  Enter Account Number or Name : ").strip().lower()
        from container import get_container
        c = get_container()
        results = c.admin_service().search_accounts(query)

        if not results:
            info("No matching accounts found.")
        else:
            for a in results:
                if a.is_frozen:
                    status_color = RED
                    status = "FROZEN"
                elif a.is_active:
                    status_color = GREEN
                    status = "ACTIVE"
                else:
                    status_color = YELLOW
                    status = "CLOSED"
                print(f"""
  {CYAN}{'─' * 40}{RESET}
  {CYAN}Account No :{WHITE} {a.account_number}{RESET}
  {CYAN}Name       :{WHITE} {a.name}{RESET}
  {CYAN}Age        :{WHITE} {a.age}{RESET}
  {CYAN}Mobile     :{WHITE} {a.mobile}{RESET}
  {CYAN}Email      :{WHITE} {a.email}{RESET}
  {CYAN}Balance    :{WHITE} {fmt_currency(float(a.balance))}{RESET}
  {CYAN}Status     :{WHITE} {status_color}{status}{RESET}
  {CYAN}Created    :{WHITE} {str(a.created_at)[:19]}{RESET}
  {CYAN}{'─' * 40}{RESET}""")
        divider()

    # ── 3. freeze / unfreeze ─────────────────────────────────────────────────

    def _freeze_account(self):
        header("FREEZE / UNFREEZE ACCOUNT")
        acc_no = input("  Enter Account Number : ").strip()

        acc = self._get_account_dict(acc_no)
        if acc is None:
            error("Account not found.")
            divider()
            return

        if not acc["is_active"] and not acc["is_frozen"]:
            error("Account is permanently closed – cannot modify.")
            divider()
            return

        currently_frozen = acc["is_frozen"]
        action = "UNFREEZE" if currently_frozen else "FREEZE"
        action_color = GREEN if currently_frozen else RED
        confirm = input(f"  {action_color}{action}{RESET} account of {CYAN}{acc['name']}{RESET}? (y/n): ").strip().lower()
        if confirm != "y":
            warning("Cancelled.")
            divider()
            return

        from container import get_container
        c = get_container()
        if currently_frozen:
            result = c.admin_service().unfreeze_account(acc_no, actor="admin")
        else:
            result = c.admin_service().freeze_account(acc_no, actor="admin")

        if result.success:
            success(result.message)
        else:
            error(result.message)
        divider()

    # ── 4. delete account ────────────────────────────────────────────────────

    def _delete_account(self):
        header("DELETE ACCOUNT")
        acc_no = input("  Enter Account Number to delete : ").strip()

        acc = self._get_account_dict(acc_no)
        if acc is None:
            print("  [!] Account not found.")
            divider()
            return

        print(f"\n  {CYAN}Account   :{WHITE} {acc_no}{RESET}")
        print(f"  {CYAN}Name      :{WHITE} {acc['name']}{RESET}")
        print(f"  {CYAN}Balance   :{WHITE} {fmt_currency(acc['balance'])}{RESET}")
        print(f"\n  {RED}{BOLD}⚠  WARNING: This will permanently delete ALL data for this account!{RESET}")
        confirm = input(f"  {YELLOW}Type 'DELETE' to confirm :{RESET} ").strip()
        if confirm != "DELETE":
            warning("Cancelled.")
            divider()
            return

        from container import get_container
        c = get_container()
        result = c.admin_service().delete_account(acc_no, actor="admin")
        if result.success:
            success(result.message)
        else:
            error(result.message)
        divider()

    # ── 5. bank statistics ────────────────────────────────────────────────────

    def _bank_statistics(self):
        header("BANK STATISTICS")
        from container import get_container
        c = get_container()
        s = c.admin_service().get_statistics()

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

    # ── 7. Loan Management ──────────────────────────────────────────────────────

    def _loan_management(self):
        header("LOAN MANAGEMENT")
        from container import get_container
        c = get_container()

        stats = c.loan_service().get_loan_statistics()

        print(f"""
  {GREEN}{'┌' + '─' * 50 + '┐'}{RESET}
  {GREEN}│{RESET}  {BOLD}LOAN MANAGEMENT{RESET}{' ' * 33}{GREEN}│{RESET}
  {GREEN}{'├' + '─' * 50 + '┤'}{RESET}
  {GREEN}│{RESET}  Pending      : {YELLOW}{stats['total_pending']:<5}{RESET}                         {GREEN}│{RESET}
  {GREEN}│{RESET}  Approved     : {GREEN}{stats['total_approved']:<5}{RESET}                         {GREEN}│{RESET}
  {GREEN}│{RESET}  Active       : {CYAN}{stats['total_active']:<5}{RESET}                         {GREEN}│{RESET}
  {GREEN}│{RESET}  Closed       : {WHITE}{stats['total_closed']:<5}{RESET}                         {GREEN}│{RESET}
  {GREEN}│{RESET}  Rejected     : {RED}{stats['total_rejected']:<5}{RESET}                         {GREEN}│{RESET}
  {GREEN}│{RESET}  Total Disbursed : {WHITE}{fmt_currency(stats['total_disbursed']):<20}{RESET} {GREEN}│{RESET}
  {GREEN}│{RESET}  Outstanding  : {YELLOW}{fmt_currency(stats['total_outstanding']):<20}{RESET} {GREEN}│{RESET}
  {GREEN}{'└' + '─' * 50 + '┘'}{RESET}""")

        print("""
  1) View Pending Loans
  2) Approve Loan
  3) Reject Loan
  4) View All Loans
  5) Back""")

        sub = input("  Enter choice: ").strip()

        if sub == "1":
            pending = c.loan_service().list_pending()
            if not pending:
                info("No pending loan applications.")
            else:
                for l in pending:
                    account = c.account_repo().get(l.account_number)
                    name = account.name if account else "Unknown"
                    print(f"""
  {CYAN}{'─' * 55}{RESET}
  {CYAN}Loan ID      :{WHITE} {l.loan_id}{RESET}
  {CYAN}Account      :{WHITE} {l.account_number} ({name}){RESET}
  {CYAN}Type         :{WHITE} {l.loan_type}{RESET}
  {CYAN}Principal    :{WHITE} {fmt_currency(float(l.principal_amount))}{RESET}
  {CYAN}Interest     :{WHITE} {l.interest_rate}% p.a.{RESET}
  {CYAN}Tenure       :{WHITE} {l.tenure_months} months{RESET}
  {CYAN}EMI          :{WHITE} {fmt_currency(float(l.emi_amount))}/month{RESET}
  {CYAN}Purpose      :{WHITE} {l.purpose or "N/A"}{RESET}
  {CYAN}Applied      :{WHITE} {str(l.application_date)[:19]}{RESET}
  {CYAN}{'─' * 55}{RESET}""")
            divider()

        elif sub == "2":
            loan_id = input("  Enter Loan ID to approve: ").strip()
            loan = c.loan_service().get_loan(loan_id)
            if not loan:
                error("Loan not found.")
            elif loan.status != "PENDING":
                error(f"Loan is already {loan.status.lower()}.")
            else:
                confirm = input(f"  Approve {fmt_currency(float(loan.principal_amount))} {loan.loan_type} loan? (y/n): ").strip().lower()
                if confirm == "y":
                    result = c.loan_service().approve_loan(loan_id=loan_id, admin_user="admin")
                    if result.success:
                        success(result.message)
                    else:
                        error(result.message)
                else:
                    warning("Cancelled.")
            divider()

        elif sub == "3":
            loan_id = input("  Enter Loan ID to reject: ").strip()
            reason = input("  Reason for rejection (optional): ").strip()
            loan = c.loan_service().get_loan(loan_id)
            if not loan:
                error("Loan not found.")
            elif loan.status != "PENDING":
                error(f"Loan is already {loan.status.lower()}.")
            else:
                confirm = input(f"  Reject {loan.loan_type} loan for {loan.account_number}? (y/n): ").strip().lower()
                if confirm == "y":
                    result = c.loan_service().reject_loan(loan_id=loan_id, reason=reason, admin_user="admin")
                    if result.success:
                        info(result.message)
                    else:
                        error(result.message)
                else:
                    warning("Cancelled.")
            divider()

        elif sub == "4":
            all_loans = c.loan_service().list_all()
            if not all_loans:
                info("No loans found.")
            else:
                print(f"  {BOLD}{'LOAN ID':<18} {'ACCOUNT':<12} {'TYPE':<14} {'PRINCIPAL':>12} {'STATUS':<12} APPLIED{RESET}")
                print(f"  {CYAN}{"-" * 72}{RESET}")
                for l in all_loans:
                    status_color = {
                        "PENDING": YELLOW, "APPROVED": GREEN,
                        "ACTIVE": CYAN, "CLOSED": WHITE, "REJECTED": RED,
                    }.get(l.status, WHITE)
                    print(f"  {l.loan_id:<18} {l.account_number:<12} {l.loan_type:<14} "
                          f"{fmt_currency(float(l.principal_amount)):>12}  "
                          f"{status_color}{l.status:<12}{RESET} {str(l.application_date)[:10]}")
            divider()

        elif sub == "5":
            pass
        else:
            error("Invalid choice.")

    # ── 6. view all transactions ─────────────────────────────────────────────

    def _view_all_transactions(self):
        header("ALL TRANSACTIONS")
        from container import get_container
        c = get_container()

        acc_filter = input(f"  {CYAN}Filter by Account Number (or press Enter to show all):{RESET} ").strip()

        if acc_filter:
            domain_txns = c.transaction_repo().get_by_account(acc_filter)
        else:
            domain_txns = c.transaction_repo().get_all()

        if not domain_txns:
            print("  No transactions recorded yet.")
            divider()
            return

        from domain.entities import TransactionType

        # Group transactions by account number (preserving original UX)
        txns_by_account: dict[str, list] = {}
        for txn in domain_txns:
            acc_no = txn.account_number
            if acc_no not in txns_by_account:
                txns_by_account[acc_no] = []
            txns_by_account[acc_no].append(txn)

        count = 0
        for acc_no, records in txns_by_account.items():
            if acc_filter and acc_no != acc_filter:
                continue
            print(f"\n  {GREEN}Account: {BOLD}{acc_no}{RESET}")
            print(f"  {CYAN}{"-" * 70}{RESET}")
            for txn in records:
                sign = "+" if txn.type in (TransactionType.DEPOSIT, TransactionType.TRANSFER_IN) else "-"
                amt_color = GREEN if sign == "+" else RED
                print(f"  [{txn.txn_id}]  {str(txn.timestamp)[:19]}  "
                      f"{txn.type.value:<14}  {amt_color}{sign}{fmt_currency(float(txn.amount))}{RESET}  "
                      f"Bal: {fmt_currency(float(txn.balance))}")
                count += 1

        print(f"\n  {WHITE}Total records shown: {BOLD}{count}{RESET}")
        divider()

    # ── 7. change admin password ─────────────────────────────────────────────

    def _change_admin_password(self):
        header("CHANGE ADMIN PASSWORD")
        old = prompt_password("  Current Password : ")

        from container import get_container
        c = get_container()
        # Use a flexible lookup — try the known admin or use the first available
        admin = c.admin_repo().get_by_username("simon") or c.admin_repo().get_by_username("admin")
        if not admin or not verify_password(old, admin.password):
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

        c.admin_repo().update_password("simon", hash_password(new))
        c.admin_repo().commit()
        logger.info("Admin password changed successfully.")
        success("Admin password updated successfully!")
        divider()
