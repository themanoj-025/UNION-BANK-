"""
seed_data.py  –  Generate ~5,000 sample accounts with transaction history.

Usage:
    python seed_data.py         # (takes ~10-15 seconds due to bcrypt)
    python seed_data.py --fast  # (uses pre-computed hash, ~2 seconds)

WARNING: This will OVERWRITE existing accounts.json and transactions.json.
Backups are automatically created (.bak files) by the save_json function.
"""

import json
import os
import random
import string
import sys
import time
from datetime import datetime, timedelta

# Ensure project root is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from utils import hash_password, TRANSACTION_CATEGORIES


# ── Configuration ────────────────────────────────────────────────────────────
NUM_ACCOUNTS = 5000
MIN_TXNS_PER_ACCOUNT = 8
MAX_TXNS_PER_ACCOUNT = 20
DEFAULT_PASSWORD = "Seed@123"
START_DATE = datetime(2025, 8, 1)  # 10 months of history
END_DATE = datetime(2026, 6, 2)

ACCOUNTS_FILE = os.path.join(BASE_DIR, "data", "accounts.json")
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "data", "transactions.json")


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
CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata",
    "Pune", "Jaipur", "Surat", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane",
    "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara",
]

TRANSACTION_TYPES = ["DEPOSIT", "WITHDRAW", "TRANSFER_OUT", "TRANSFER_IN"]
TXN_WEIGHTS = [0.40, 0.30, 0.15, 0.15]  # 40% deposits, 30% withdrawals, etc.

# Map transaction types to likely categories
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
    """Generate a random datetime between start and end."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_phone() -> str:
    """Generate a valid Indian mobile number (10 digits, starts with 6-9)."""
    return str(random.randint(6, 9)) + "".join([str(random.randint(0, 9)) for _ in range(9)])


def generate_email(name: str) -> str:
    """Generate a plausible email from a name."""
    name_clean = name.lower().replace(" ", ".")
    domains = ["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com", "hotmail.com", "email.com"]
    domain = random.choice(domains)
    suffixes = ["", str(random.randint(1, 999)), str(random.randint(1990, 2005))]
    suffix = random.choice(suffixes)
    if suffix:
        return f"{name_clean}{suffix}@{domain}"
    return f"{name_clean}@{domain}"


def generate_account_number(used_numbers: set) -> str:
    """Generate a unique 10-digit account number."""
    while True:
        num = str(random.randint(1000000000, 9999999999))
        if num not in used_numbers:
            used_numbers.add(num)
            return num


_TXN_CHARS = string.ascii_uppercase + string.digits

def generate_txn_id() -> str:
    """Generate a unique transaction ID."""
    return "TXN-" + "".join(random.choices(_TXN_CHARS, k=8))


# ── Main seeding function ────────────────────────────────────────────────────

def seed_data(fast_mode: bool = True):
    """
    Generate sample data and write to accounts.json and transactions.json.

    Args:
        fast_mode: If True, use a single pre-computed bcrypt hash for all accounts
                   (much faster, ~2 seconds vs ~15 seconds for 5000 accounts).
    """
    print(f"\n  {'=' * 50}")
    print(f"  Seeding {NUM_ACCOUNTS:,} sample accounts...")
    print(f"  {'=' * 50}\n")

    # Pre-compute password hash (or use fast mode)
    if fast_mode:
        print("  Fast mode: using single hash for all accounts")
        hashed_password = hash_password(DEFAULT_PASSWORD)
    else:
        print(f"  Hashing password '{DEFAULT_PASSWORD}' for each account...")
        hashed_password = None  # Will hash per-account

    accounts = {}
    transactions = {}
    used_account_numbers = set()

    # Track existing account numbers to avoid collisions
    if os.path.exists(ACCOUNTS_FILE):
        from utils import load_json
        existing = load_json(ACCOUNTS_FILE)
        used_account_numbers.update(existing.keys())
        print(f"  Found {len(existing)} existing accounts - avoiding collisions")

    start_time = time.time()

    for i in range(NUM_ACCOUNTS):
        # Pick name
        gender = random.choice(GENDERS)
        first_name = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"

        # Generate account number
        acc_no = generate_account_number(used_account_numbers)

        # Personal details
        age = random.randint(18, 75)
        mobile = generate_phone()
        email = generate_email(full_name)
        # Initial balance between ₹500 and ₹5,00,000
        initial_balance = round(random.uniform(500, 500000), 2)

        # Created date (random over the past 10 months)
        created_date = random_date(START_DATE, END_DATE - timedelta(days=30))
        created_str = created_date.strftime("%Y-%m-%d %H:%M:%S")

        # Hash password
        if fast_mode:
            pwd_hash = hashed_password
        else:
            pwd_hash = hash_password(DEFAULT_PASSWORD)

        # Build account record
        accounts[acc_no] = {
            "account_number": acc_no,
            "name": full_name,
            "age": age,
            "gender": gender,
            "mobile": mobile,
            "email": email,
            "password": pwd_hash,
            "balance": initial_balance,
            "is_active": True,
            "is_frozen": False,
            "created_at": created_str,
        }

        # Generate transactions for this account
        num_txns = random.randint(MIN_TXNS_PER_ACCOUNT, MAX_TXNS_PER_ACCOUNT)
        acc_transactions = []
        running_balance = initial_balance

        # Generate dates spread across the account's lifetime
        txn_dates = sorted([random_date(created_date, END_DATE) for _ in range(num_txns)])

        for txn_date in txn_dates:
            txn_type = random.choices(TRANSACTION_TYPES, weights=TXN_WEIGHTS, k=1)[0]
            category = random.choice(TYPE_CATEGORY_MAP[txn_type])

            if txn_type == "DEPOSIT":
                amount = round(random.uniform(500, 100000), 2)
                running_balance += amount
                description = random.choice(DEPOSIT_DESCRIPTIONS)
            elif txn_type == "WITHDRAW":
                max_wd = max(100, running_balance * 0.3)  # Don't withdraw more than 30%
                amount = round(random.uniform(50, min(max_wd, 50000)), 2)
                running_balance -= amount
                description = random.choice(WITHDRAW_DESCRIPTIONS)
            elif txn_type == "TRANSFER_OUT":
                max_tr = max(100, running_balance * 0.5)
                amount = round(random.uniform(100, min(max_tr, 25000)), 2)
                running_balance -= amount
                description = random.choice(TRANSFER_OUT_DESCRIPTIONS)
            else:  # TRANSFER_IN
                amount = round(random.uniform(500, 50000), 2)
                running_balance += amount
                description = random.choice(TRANSFER_IN_DESCRIPTIONS)

            running_balance = round(running_balance, 2)
            if running_balance < 0:
                running_balance = 0  # Safety net

            txn_record = {
                "txn_id": generate_txn_id(),
                "type": txn_type,
                "amount": amount,
                "description": description,
                "balance": running_balance,
                "timestamp": txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                "category": category,
            }
            # Only add target_account for transfers (simulated)
            if txn_type in ("TRANSFER_OUT", "TRANSFER_IN"):
                txn_record["target_account"] = "XXXXXXXXXX"

            acc_transactions.append(txn_record)

        # Update final balance
        accounts[acc_no]["balance"] = running_balance
        transactions[acc_no] = acc_transactions

        # Progress indicator
        if (i + 1) % 500 == 0 or i == 0:
            elapsed = time.time() - start_time
            pct = (i + 1) / NUM_ACCOUNTS * 100
            print(f"  [{i+1:>5,}/{NUM_ACCOUNTS:,}] accounts generated ({pct:.0f}%) - {elapsed:.1f}s")

    # ── Write to files ───────────────────────────────────────────────────────
    from utils import save_json

    print(f"\n  Writing accounts to {ACCOUNTS_FILE}...")
    save_json(ACCOUNTS_FILE, accounts)

    print(f"  Writing transactions to {TRANSACTIONS_FILE}...")
    save_json(TRANSACTIONS_FILE, transactions)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_txns = sum(len(v) for v in transactions.values())
    total_balance = sum(a["balance"] for a in accounts.values())
    elapsed = time.time() - start_time

    print(f"\n  {'=' * 50}")
    print(f"  Seeding Complete!")
    print(f"  {'=' * 50}")
    print(f"     Accounts      : {len(accounts):>8,}")
    print(f"     Transactions  : {total_txns:>8,}")
    print(f"     Avg txns/acct : {total_txns / len(accounts):>8.1f}")
    print(f"     Total balance : Rs.{total_balance:>12,.2f}")
    print(f"     Time taken    : {elapsed:>8.1f}s")
    # print(f"     Default pwd   : {DEFAULT_PASSWORD}")  # Redacted for security
    print(f"  {'=' * 50}\n")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fast_mode = "--slow" not in sys.argv  # Fast by default (--slow for per-account hashing)
    seed_data(fast_mode=fast_mode)
