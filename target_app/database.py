"""
Database Layer - ALL database operations go here.

This file ONLY:
- Connects to database
- Runs queries
- Returns data

No Flask routes here! No business logic here!
Just: "Get member from DB", "Save member to DB", etc.
"""

import sqlite3
import os
from typing import Optional, List, Dict, Any

from target_app.models import Member, Account, Transaction

DATABASE = "target_app/members.db"


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    """Initialize database schema and sample data."""
    if os.path.exists(DATABASE):
        return  # Already initialized
    
    db = get_db()
    cursor = db.cursor()
    
    # ============ CREATE TABLES ============
    
    cursor.execute("""
        CREATE TABLE members (
            id INTEGER PRIMARY KEY,
            member_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            phone TEXT,
            joined_date TEXT,
            account_status TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            member_id TEXT,
            account_type TEXT,
            balance REAL,
            last_transaction TEXT,
            FOREIGN KEY(member_id) REFERENCES members(member_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            member_id TEXT,
            account_type TEXT,
            amount REAL,
            description TEXT,
            transaction_date TEXT,
            FOREIGN KEY(member_id) REFERENCES members(member_id)
        )
    """)
    
    # ============ INSERT SAMPLE DATA ============
    
    members_data = [
        ("M001", "John Doe", "john@example.com", "555-0101", "2020-01-15", "active"),
        ("M002", "Jane Smith", "jane@example.com", "555-0102", "2021-03-20", "active"),
        ("M003", "Bob Johnson", "bob@example.com", "555-0103", "2019-11-10", "active"),
        ("M004", "Alice Williams", "alice@example.com", "555-0104", "2022-06-05", "active"),
        ("M005", "Charlie Brown", "charlie@example.com", "555-0105", "2021-09-12", "inactive"),
    ]
    
    for member_id, name, email, phone, joined_date, status in members_data:
        cursor.execute(
            "INSERT INTO members VALUES (NULL, ?, ?, ?, ?, ?, ?)",
            (member_id, name, email, phone, joined_date, status)
        )
    
    accounts_data = [
        ("M001", "Checking", 5234.50, "2026-08-12"),
        ("M001", "Savings", 12750.25, "2026-08-10"),
        ("M002", "Checking", 3100.00, "2026-08-13"),
        ("M002", "Savings", 25600.75, "2026-08-12"),
        ("M003", "Checking", 1500.50, "2026-08-11"),
        ("M003", "Savings", 8200.00, "2026-08-09"),
        ("M004", "Checking", 4800.25, "2026-08-13"),
        ("M004", "Savings", 15400.00, "2026-08-12"),
        ("M005", "Checking", 200.00, "2026-08-01"),
        ("M005", "Savings", 5000.00, "2026-07-15"),
    ]
    
    for member_id, account_type, balance, last_txn in accounts_data:
        cursor.execute(
            "INSERT INTO accounts VALUES (NULL, ?, ?, ?, ?)",
            (member_id, account_type, balance, last_txn)
        )
    
    db.commit()
    db.close()


# ============ MEMBER QUERIES ============

def find_member_by_id(member_id: str) -> Optional[Member]:
    """Get member by ID from database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
    row = cursor.fetchone()
    db.close()
    
    if not row:
        return None
    
    return Member(
        member_id=row['member_id'],
        name=row['name'],
        email=row['email'],
        phone=row['phone'],
        joined_date=row['joined_date'],
        account_status=row['account_status'],
    )


def search_members(search_term: str) -> List[Member]:
    """Search members by ID or name."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM members WHERE member_id LIKE ? OR name LIKE ?",
        (f"%{search_term}%", f"%{search_term}%")
    )
    rows = cursor.fetchall()
    db.close()
    
    members = []
    for row in rows:
        members.append(Member(
            member_id=row['member_id'],
            name=row['name'],
            email=row['email'],
            phone=row['phone'],
            joined_date=row['joined_date'],
            account_status=row['account_status'],
        ))
    return members


# ============ ACCOUNT QUERIES ============

def get_member_accounts(member_id: str) -> List[Account]:
    """Get all accounts for a member."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM accounts WHERE member_id = ?", (member_id,))
    rows = cursor.fetchall()
    db.close()
    
    accounts = []
    for row in rows:
        accounts.append(Account(
            account_id=row['id'],
            member_id=row['member_id'],
            account_type=row['account_type'],
            balance=row['balance'],
            last_transaction=row['last_transaction'],
        ))
    return accounts


def get_account_balance(member_id: str, account_type: str) -> Optional[float]:
    """Get balance for specific account."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT balance FROM accounts WHERE member_id = ? AND account_type = ?",
        (member_id, account_type)
    )
    row = cursor.fetchone()
    db.close()
    
    return row['balance'] if row else None


# ============ TRANSACTION QUERIES ============

def get_member_transactions(member_id: str, limit: int = 10) -> List[Transaction]:
    """Get recent transactions for a member."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM transactions WHERE member_id = ? ORDER BY transaction_date DESC LIMIT ?",
        (member_id, limit)
    )
    rows = cursor.fetchall()
    db.close()
    
    transactions = []
    for row in rows:
        transactions.append(Transaction(
            transaction_id=row['id'],
            member_id=row['member_id'],
            account_type=row['account_type'],
            amount=row['amount'],
            description=row['description'],
            transaction_date=row['transaction_date'],
        ))
    return transactions
