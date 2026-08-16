"""Service layer for member business logic."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from target_app.models import Member
from target_app.repositories.member_repository import MemberRepository


class MemberService(ABC):
    """Business service contract for member operations."""

    @abstractmethod
    def search_member(self, search_term: str) -> List[Member]:
        """Return members matching the supplied search term."""

    @abstractmethod
    def search_members(self, search_term: str) -> Dict[str, object]:
        """Return a controller-friendly search result payload."""

    @abstractmethod
    def get_member_detail(self, member_id: str) -> Optional[Dict[str, object]]:
        """Return full member detail and account/transaction history."""

    @abstractmethod
    def prepare_update_context(self, member_id: str) -> Optional[Dict[str, object]]:
        """Prepare the update form context."""

    @abstractmethod
    def handle_balance_update(self, member_id: str, action: str, pending: Optional[Dict[str, object]]) -> Dict[str, object]:
        """Handle confirm/cancel balance update workflow."""


class DefaultMemberService(MemberService):
    """Concrete implementation of the member business service."""

    def __init__(self, repository: MemberRepository):
        self.repository = repository

    def search_member(self, search_term: str) -> List[Member]:
        normalized = (search_term or "").strip()
        if not normalized:
            return []
        return self.repository.search(normalized)

    def search_members(self, search_term: str) -> Dict[str, object]:
        normalized = (search_term or "").strip()

        if not normalized:
            return {
                "results": [],
                "search_term": "",
                "error": "Please enter a member ID or name",
            }

        results = self.search_member(normalized)
        if not results:
            return {
                "results": [],
                "search_term": normalized,
                "error": f"No members found matching '{normalized}'",
            }

        return {
            "results": results,
            "search_term": normalized,
            "error": None,
        }

    def get_member_detail(self, member_id: str) -> Optional[Dict[str, object]]:
        member = self.repository.find_by_id(member_id)
        if not member:
            return None

        accounts = self.repository.get_accounts(member_id)
        transactions = self.repository.get_transactions(member_id, limit=5)

        return {
            "member": member,
            "accounts": accounts,
            "transactions": transactions,
        }

    def prepare_update_context(self, member_id: str) -> Optional[Dict[str, object]]:
        detail = self.get_member_detail(member_id)
        if not detail:
            return None

        return {
            "member": detail["member"],
            "accounts": detail["accounts"],
        }

    def handle_balance_update(self, member_id: str, action: str, pending: Optional[Dict[str, object]]) -> Dict[str, object]:
        if action == "cancel":
            return {
                "status": "cancelled",
                "redirect_to": "member_detail",
                "member_id": member_id,
            }

        if action == "confirm":
            if not pending:
                raise ValueError("No pending balance update exists.")

            member = self.repository.find_by_id(member_id)
            if not member:
                raise ValueError(f"Member '{member_id}' not found.")

            return {
                "status": "confirmed",
                "redirect_to": "update_result",
                "member_id": member_id,
                "result": {
                    "success": True,
                    "message": f"Balance updated successfully for {member.name}",
                    "updated_at": datetime.now().isoformat(),
                    "account_type": pending.get("account_type"),
                    "new_balance": pending.get("new_balance"),
                },
            }

        raise ValueError(f"Unsupported action '{action}'.")
