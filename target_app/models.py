"""
Data Models - Define the structure of our data.

This file ONLY defines:
- What is a Member?
- What is an Account?
- What is a Transaction?

No database operations here! Just the data shapes.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Member:
    """Represents a bank member."""
    member_id: str
    name: str
    email: str
    phone: str
    joined_date: str
    account_status: str  # "active" or "inactive"
    
    def __dict__(self):
        """Convert to dictionary (for JSON)."""
        return {
            'member_id': self.member_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'joined_date': self.joined_date,
            'account_status': self.account_status,
        }


@dataclass
class Account:
    """Represents a bank account (Checking, Savings, etc)."""
    account_id: int
    member_id: str
    account_type: str  # "Checking" or "Savings"
    balance: float
    last_transaction: str  # Date string
    
    def __dict__(self):
        return {
            'id': self.account_id,
            'member_id': self.member_id,
            'account_type': self.account_type,
            'balance': self.balance,
            'last_transaction': self.last_transaction,
        }


@dataclass
class Transaction:
    """Represents a transaction."""
    transaction_id: int
    member_id: str
    account_type: str
    amount: float
    description: str
    transaction_date: str
    
    def __dict__(self):
        return {
            'id': self.transaction_id,
            'member_id': self.member_id,
            'account_type': self.account_type,
            'amount': self.amount,
            'description': self.description,
            'transaction_date': self.transaction_date,
        }
