"""ui.py  –  Centralised terminal-UI helpers for Union Bank.

Provides colored output (via colorama), password masking (via getpass),
and consistent styling for all terminal interactions.
"""

import getpass
import os
import sys

from colorama import Back, Fore, Style
from colorama import init as colorama_init

# ── Initialise colorama (required on Windows) ───────────────────────────────
colorama_init(autoreset=True)

# ── Color aliases ────────────────────────────────────────────────────────────
GREEN   = Fore.GREEN
RED     = Fore.RED
YELLOW  = Fore.YELLOW
CYAN    = Fore.CYAN
MAGENTA = Fore.MAGENTA
BLUE    = Fore.BLUE
WHITE   = Fore.WHITE
BOLD    = Style.BRIGHT
RESET   = Style.RESET_ALL

_DIM = Style.DIM


# ── Styled print helpers ─────────────────────────────────────────────────────

def success(msg: str) -> None:
    """Print a success message with a green checkmark."""
    print(f"{GREEN}  [✓] {msg}{RESET}")


def error(msg: str) -> None:
    """Print an error message with a red cross."""
    print(f"{RED}  [!] {msg}{RESET}")


def warning(msg: str) -> None:
    """Print a warning message in yellow."""
    print(f"{YELLOW}  [!] {msg}{RESET}")


def info(msg: str) -> None:
    """Print an info message in cyan."""
    print(f"{CYAN}  {msg}{RESET}")


def highlight(msg: str) -> None:
    """Print a highlighted message in magenta."""
    print(f"{MAGENTA}  {msg}{RESET}")


def dim(msg: str) -> None:
    """Print a dimmed/less prominent message."""
    print(f"{_DIM}{msg}{RESET}")


# ── Structural helpers ───────────────────────────────────────────────────────

def header(title: str, char: str = "═", width: int = 50) -> None:
    """Print a section header with a coloured horizontal rule."""
    rule = char * width
    print(f"\n{BLUE}{BOLD}{rule}{RESET}")
    print(f"{BLUE}{BOLD}  {title}{RESET}")
    print(f"{BLUE}{BOLD}{rule}{RESET}")


def divider(char: str = "─", width: int = 50) -> None:
    """Print a coloured horizontal divider."""
    print(f"{BLUE}{char * width}{RESET}")


def sub_header(title: str) -> None:
    """Print a sub-section header."""
    print(f"\n{CYAN}{BOLD}  ── {title} ──{RESET}")


# ── Password input ───────────────────────────────────────────────────────────

def prompt_password(prompt: str = "  Password: ") -> str:
    """Prompt for a password with masking (characters not echoed)."""
    return getpass.getpass(prompt)


def prompt_new_password(prompt: str = "  Enter new password: ") -> str:
    """Prompt for a new password with masking."""
    return getpass.getpass(prompt)


# ── Clear screen ─────────────────────────────────────────────────────────────

def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


# ── Input with colour ────────────────────────────────────────────────────────

def colored_input(prompt: str, color: str = CYAN) -> str:
    """Prompt for input with a coloured prompt string."""
    return input(f"{color}{prompt}{RESET}")


# ── Table row ────────────────────────────────────────────────────────────────

def table_header(*columns: str) -> None:
    """Print a table header row with bold text."""
    header_line = "  " + "  ".join(columns)
    print(f"{BOLD}{header_line}{RESET}")


def table_row(*columns: str) -> None:
    """Print a table data row."""
    print("  " + "  ".join(columns))
