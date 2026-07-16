"""
seed_data.py  –  Generate ~5,000 sample accounts with transaction history.

Writes directly to SQLite via the repository layer (no JSON files).

Usage:
    python seed_data.py         # (takes ~10-15 seconds due to bcrypt)
    python seed_data.py --slow  # (hashes each password individually, ~15 seconds)
    python seed_data.py --fast  # (pre-computed hash, ~2 seconds — default)
"""

import os
import random
import secrets
import string
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Set testing-friendly env vars so Config doesn't require real secrets
os.environ.setdefault("UNION_BANK_TESTING", "1")
os.environ.setdefault("JWT_SECRET", "seed-data-secret")
os.environ.setdefault("FLASK_SECRET_KEY", "seed-data-flask-key")

from unionbank.utils.hashing import hash_password
from unionbank.config import settings

# ── Configuration ────────────────────────────────────────────────────────────
NUM_ACCOUNTS = 5000
MIN_TXNS_PER_ACCOUNT = 8
MAX_TXNS_PER_ACCOUNT = 20
DEFAULT_PASSWORD = "Seed@123"
START_DATE = datetime(2025, 8, 1)  # 10 months of history
END_DATE = datetime(2026, 6, 2)

TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES


# ── Indian names data ────────────────────────────────────────────────────────

FIRST_NAMES_MALE = [
    "Aarav", "Arjun", "Vivaan", "Aditya", "Vihaan", "Arush", "Ayaan", "Ishaan",
    "Shaurya", "Dhruv", "Reyansh", "Krishna", "Yash", "Kabir", "Rudra", "Om",
    "Ranveer", "Shiv", "Aryan", "Rohan", "Abhimanyu", "Akhil", "Aniket", "Bhavesh",
    "Chirag", "Darshan", "Devendra", "Dhruv", "Gaurav", "Harsh", "Hitesh", "Ishaan",
    "Jatin", "Karan", "Kunal", "Lalit", "Manav", "Manish", "Manoj", "Mitesh",
    "Naman", "Nikhil", "Nitin", "Omkar", "Pranav", "Prashant", "Rahul", "Rajesh",
    "Rakesh", "Ravi", "Rohit", "Sachin", "Sameer", "Sandeep", "Sanjay", "Sarthak",
    "Shubham", "Siddharth", "Soham", "Sumit", "Suraj", "Tanmay", "Uday", "Varun",
    "Vikram", "Vishal", "Yashwant", "Akshay", "Amit", "Anand", "Arun", "Ashok",
    "Deepak", "Ganesh", "Hemant", "Jayesh", "Kiran", "Mahesh", "Mohan", "Naresh",
    "Navneet", "Pankaj", "Prakash", "Rajendra", "Ramesh", "Santosh", "Satyam",
    "Shekhar", "Suresh", "Tushar", "Umesh", "Vijay", "Vinay", "Yogesh", "Akash",
    "Aman", "Anuj", "Ayush", "Chetan", "Dinesh", "Girish", "Harish", "Jagdish",
    "Lokesh", "Mukesh", "Naveen", "Parag", "Pushkar", "Rajeev", "Ranjan", "Sagar",
    "Shankar", "Shyam", "Sudhir", "Swapnil", "Trilok", "Vikas", "Vinod", "Wasim",
]

FIRST_NAMES_FEMALE = [
    "Aadhya", "Aanya", "Aarushi", "Aditi", "Ananya", "Anika", "Anjali", "Anushka",
    "Avani", "Bhavna", "Charvi", "Devika", "Disha", "Divya", "Esha", "Gargi",
    "Gauri", "Geeta", "Isha", "Ishita", "Jhanvi", "Kajal", "Kavya", "Khushi",
    "Kiara", "Kriti", "Lavanya", "Madhuri", "Maya", "Meera", "Neha", "Nidhi",
    "Nisha", "Pallavi", "Pooja", "Prachi", "Pragya", "Prerna", "Priya", "Priyanka",
    "Radhika", "Ragini", "Ritika", "Riya", "Roshni", "Rutvi", "Sakshi", "Sana",
    "Sanskriti", "Sara", "Seema", "Shikha", "Shruti", "Simran", "Sneha", "Sonia",
    "Srishti", "Suman", "Sunita", "Swati", "Tanvi", "Tanya", "Trisha", "Urvi",
    "Vaishali", "Vandana", "Varsha", "Vidya", "Yashvi", "Zara", "Aishwarya",
    "Ankita", "Asha", "Bhavika", "Chitra", "Deepika", "Ekta", "Garima", "Hinal",
    "Jasmine", "Jyoti", "Komal", "Laxmi", "Manisha", "Mitali", "Namrata", "Neelam",
    "Nikita", "Parul", "Payal", "Rashmi", "Reema", "Reena", "Reshma", "Sangeeta",
    "Sarita", "Shalini", "Shivani", "Smita", "Sonal", "Suhani", "Tara", "Uma",
]

LAST_NAMES = [
    "Acharya", "Agarwal", "Ahuja", "Arora", "Bajaj", "Bakshi", "Bansal", "Bedi",
    "Bhat", "Bhatt", "Bhattacharya", "Bhonsle", "Bose", "Chakraborty", "Chand",
    "Chandra", "Chatterjee", "Chaudhary", "Chauhan", "Chopra", "Datta", "Dave",
    "Desai", "Deshmukh", "Deshpande", "Devi", "Dhawan", "Dixit", "Dubey", "Dutta",
    "Gandhi", "Ghosh", "Gill", "Goel", "Goswami", "Goyal", "Grewal", "Guha",
    "Gupta", "Hegde", "Iyer", "Jain", "Jaiswal", "Jha", "Joshi", "Kadam",
    "Kakkar", "Kale", "Kamat", "Kapoor", "Kar", "Karnik", "Kashyap", "Kaul",
    "Kaur", "Khanna", "Khatri", "Kohli", "Krishnan", "Kulkarni", "Kumar", "Lal",
    "Malhotra", "Malik", "Mane", "Mathur", "Mehta", "Menon", "Mishra", "Mistry",
    "Modi", "Mohanty", "Mukherjee", "Naidu", "Nair", "Nambiar", "Narang", "Nayak",
    "Nehru", "Oberoi", "Padmanabhan", "Pal", "Pandey", "Pandit", "Parekh", "Parikh",
    "Patel", "Pathak", "Patil", "Pillai", "Pradhan", "Prakash", "Prasad", "Purohit",
    "Raghavan", "Rajan", "Rajput", "Raman", "Ramaswamy", "Rana", "Ranganathan",
    "Rao", "Rathore", "Rattan", "Rawat", "Reddy", "Roy", "Sachdev", "Sahai",
    "Sahni", "Sahoo", "Saini", "Sanghvi", "Saraswat", "Sarkar", "Saxena", "Sen",
    "Sethi", "Shah", "Shankar", "Sharma", "Shenoy", "Shetty", "Shinde", "Shukla",
    "Singh", "Sinha", "Soni", "Sood", "Srinivasan", "Subramanian", "Suri", "Swaminathan",
    "Talwar", "Tandon", "Taneja", "Tewari", "Thakur", "Thapar", "Tiwari", "Trivedi",
    "Upadhyay", "Varma", "Venkatesh", "Verma", "Vyas", "Wagh", "Wankhede", "Yadav",
]

GENDERS = ["Male", "Female"]

TRANSACTION_TYPES = ["DEPOSIT", "WITHDRAW", "TRANSFER_OUT", "TRANSFER_IN"]
TXN_WEIGHTS = [0.40, 0.30, 0.15, 0.15]

TYPE_CATEGORY_MAP = {
    "DEPOSIT":       ["Salary", "Savings", "Investment", "General"],
    "WITHDRAW":      ["Food & Dining", "Transport", "Shopping", "Bills & Utilities",
                      "Entertainment", "Health", "Education", "Rent", "Other"],
    "TRANSFER_OUT":  ["General", "Investment", "Savings"],
    "TRANSFER_IN":   ["General", "Investment", "Savings"],
}

DEPOSIT_DESCRIPTIONS = [
    "Salary credit", "Cash deposit", "Cheque deposit", "Online transfer received",
    "Refund credit", "Bonus credited", "Interest credited", "Dividend payment",
]
WITHDRAW_DESCRIPTIONS = [
    "ATM withdrawal", "POS purchase", "Online payment", "UPI payment",
    "Bill payment", "Shopping payment", "Restaurant payment", "Fuel purchase",
]
TRANSFER_OUT_DESCRIPTIONS = [
    "Fund transfer", "Money sent to friend", "Family remittance", "Investment transfer",
]
TRANSFER_IN_DESCRIPTIONS = [
    "Funds received", "Money from friend", "Family remittance", "Transfer received",
]


# ── Helpers ──────────────────────────────────────────────────────────────────


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_phone() -> str:
    return str(random.randint(6, 9)) + "".join([str(random.randint(0, 9)) for _ in range(9)])


def generate_email(name: str) -> str:
    name_clean = name.lower().replace(" ", ".")
    domains = ["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com", "hotmail.com", "email.com"]
    domain = random.choice(domains)
    suffixes = ["", str(random.randint(1, 999)), str(random.randint(1990, 2005))]
    suffix = random.choice(suffixes)
    if suffix:
        return f"{name_clean}{suffix}@{domain}"
    return f"{name_clean}@{domain}"


_TXN_CHARS = string.ascii_uppercase + string.digits


def generate_txn_id() -> str:
    return "TXN-" + "".join(random.choices(_TXN_CHARS, k=8))


# ── Main seeding function ────────────────────────────────────────────────────

def seed_data(fast_mode: bool = True):
    """
    Generate sample data and write directly to SQLite via the repository layer.

    Uses SQLAlchemy metadata drop_all/create_all to reset the database —
    portable across all OSes and avoids Windows WAL-file-locking issues.

    IMPORTANT: Uses raw session.add() for AccountModel objects and updates
    them in-place to avoid the `autoflush=False` identity-map issue where
    repo.update() would create a duplicate INSERT for pending objects.

    Args:
        fast_mode: If True, use a single pre-computed bcrypt hash for all accounts
                   (much faster, ~2 seconds vs ~15 seconds for 5000 accounts).
    """
    from unionbank.infrastructure.database import (
        get_session, close_session, reset_engine, ModelBase, get_engine,
    )
    from unionbank.infrastructure.repositories import (
        SqlAlchemyTransactionRepository,
    )
    from unionbank.infrastructure.mappers import map_account_to_model
    from unionbank.infrastructure.persistence import AccountModel, TransactionModel
    from unionbank.domain.entities import Account, Transaction, TransactionType

    print(f"\n  {'=' * 50}")
    print(f"  Seeding {NUM_ACCOUNTS:,} sample accounts...")
    print(f"  {'=' * 50}\n")

    # Reset engine and drop + recreate all tables (portable, avoids Windows file-locking)
    reset_engine()
    engine = get_engine()
    ModelBase.metadata.drop_all(bind=engine)
    ModelBase.metadata.create_all(bind=engine)
    print("  Fresh database tables created via SQLAlchemy metadata.\n")

    # Pre-compute password hash
    if fast_mode:
        print("  Fast mode: using single hash for all accounts")
        hashed_password = hash_password(DEFAULT_PASSWORD)
    else:
        print(f"  Hashing password '{DEFAULT_PASSWORD}' for each account...")
        hashed_password = None

    session = get_session()
    # Use repos for transaction creation (cleaner), use raw session for accounts
    # to avoid the autoflush=False identity-map issue with repo.update()
    txn_repo = SqlAlchemyTransactionRepository(session)

    used_account_numbers = set()
    start_time = time.time()

    for i in range(NUM_ACCOUNTS):
        gender = random.choice(GENDERS)
        first_name = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"

        age = random.randint(18, 75)
        mobile = generate_phone()
        email = generate_email(full_name)
        initial_balance = round(random.uniform(500, 500000), 2)
        created_date = random_date(START_DATE, END_DATE - timedelta(days=30))
        pwd_hash = hashed_password if fast_mode else hash_password(DEFAULT_PASSWORD)

        # Generate unique account number using a Python set
        acc_no = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        while acc_no in used_account_numbers:
            acc_no = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        used_account_numbers.add(acc_no)

        account = Account(
            account_number=acc_no,
            name=full_name,
            age=age,
            gender=gender,
            mobile=mobile,
            email=email,
            password=pwd_hash,
            balance=Decimal(str(initial_balance)),
            is_active=True,
            is_frozen=False,
            created_at=created_date,
            updated_at=created_date,
        )

        # Map to ORM model and add to session directly (not via repo)
        # This gives us a reference to the model to update balance later
        data = map_account_to_model(account)
        account_model = AccountModel(**data)
        session.add(account_model)

        # Generate transactions
        num_txns = random.randint(MIN_TXNS_PER_ACCOUNT, MAX_TXNS_PER_ACCOUNT)
        running_balance = Decimal(str(initial_balance))
        txn_dates = sorted([random_date(created_date, END_DATE) for _ in range(num_txns)])

        for txn_date in txn_dates:
            txn_type = random.choices(TRANSACTION_TYPES, weights=TXN_WEIGHTS, k=1)[0]
            category = random.choice(TYPE_CATEGORY_MAP[txn_type])

            if txn_type == "DEPOSIT":
                amount = Decimal(str(round(random.uniform(500, 100000), 2)))
                running_balance += amount
                description = random.choice(DEPOSIT_DESCRIPTIONS)
            elif txn_type == "WITHDRAW":
                max_wd = max(Decimal("100"), running_balance * Decimal("0.3"))
                amount = min(Decimal(str(round(random.uniform(50, 50000), 2))), max_wd)
                running_balance -= amount
                description = random.choice(WITHDRAW_DESCRIPTIONS)
            elif txn_type == "TRANSFER_OUT":
                max_tr = max(Decimal("100"), running_balance * Decimal("0.5"))
                amount = min(Decimal(str(round(random.uniform(100, 25000), 2))), max_tr)
                running_balance -= amount
                description = random.choice(TRANSFER_OUT_DESCRIPTIONS)
            else:
                amount = Decimal(str(round(random.uniform(500, 50000), 2)))
                running_balance += amount
                description = random.choice(TRANSFER_IN_DESCRIPTIONS)

            if running_balance < 0:
                running_balance = Decimal("0")

            txn = Transaction(
                txn_id=generate_txn_id(),
                account_number=acc_no,
                type=TransactionType(txn_type),
                amount=amount,
                balance=running_balance,
                description=description,
                category=category,
                timestamp=txn_date,
            )
            txn_repo.create(txn)

        # Update the account model's balance directly (avoids repo.update()
        # which would create a duplicate INSERT with autoflush=False)
        account_model.balance = running_balance

        if (i + 1) % 500 == 0 or i == 0:
            elapsed = time.time() - start_time
            pct = (i + 1) / NUM_ACCOUNTS * 100
            print(f"  [{i+1:>5,}/{NUM_ACCOUNTS:,}] accounts generated ({pct:.0f}%) - {elapsed:.1f}s")

    session.commit()

    total_txns = txn_repo.count()
    total_accounts = session.query(AccountModel).count()
    from sqlalchemy import func
    total_balance = float(
        session.query(func.sum(AccountModel.balance))
        .filter(AccountModel.is_active.is_(True), AccountModel.is_frozen.is_(False))
        .scalar() or Decimal("0.00")
    )
    elapsed = time.time() - start_time

    close_session()

    print(f"\n  {'=' * 50}")
    print(f"  Seeding Complete!")
    print(f"  {'=' * 50}")
    print(f"     Accounts      : {total_accounts:>8,}")
    print(f"     Transactions  : {total_txns:>8,}")
    if total_accounts:
        print(f"     Avg txns/acct : {total_txns / total_accounts:>8.1f}")
    print(f"     Total balance : Rs.{total_balance:>12,.2f}")
    print(f"     Time taken    : {elapsed:>8.1f}s")
    print(f"  {'=' * 50}\n")


if __name__ == "__main__":
    fast_mode = "--slow" not in sys.argv
    seed_data(fast_mode=fast_mode)
