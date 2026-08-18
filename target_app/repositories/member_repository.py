"""Repository layer for member data access."""

from typing import List, Optional

from target_app.database import (
    find_member_by_id,
    get_member_accounts,
    get_member_transactions,
    search_members,
        update_account_balance,
)
from target_app.models import Member, Account, Transaction


class MemberRepository:
    """Repository responsible for member persistence and queries."""

    def find_by_id(self, member_id: str) -> Optional[Member]:
        return find_member_by_id(member_id)

    def search(self, search_term: str) -> List[Member]:
        return search_members(search_term)

    def get_accounts(self, member_id: str) -> List[Account]:
        return get_member_accounts(member_id)

    def get_transactions(self, member_id: str, limit: int = 5) -> List[Transaction]:
        return get_member_transactions(member_id, limit=limit)

    def update_balance(self, member_id: str, account_type: str, new_balance: float) -> None:
        update_account_balance(member_id, account_type, new_balance)
