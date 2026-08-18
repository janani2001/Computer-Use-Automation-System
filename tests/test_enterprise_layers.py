from target_app.repositories.member_repository import MemberRepository
from target_app.services.member_service import DefaultMemberService


def test_member_repository_works():
    repo = MemberRepository()
    member = repo.find_by_id("M001")
    assert member is not None
    assert member.member_id == "M001"
    assert member.name == "John Doe"


def test_member_service_works():
    service = DefaultMemberService(MemberRepository())
    results = service.search_member("John")
    assert len(results) >= 1
    assert results[0].member_id == "M001"

    detail = service.get_member_detail("M001")
    assert detail["member"].member_id == "M001"
    assert len(detail["accounts"]) >= 2


def test_member_service_rejects_missing_pending_update():
    service = DefaultMemberService(MemberRepository())

    try:
        service.handle_balance_update("M001", "confirm", None)
    except ValueError as exc:
        assert str(exc) == "No pending balance update exists."
    else:
        raise AssertionError("Expected missing pending update to be rejected")


def test_member_service_rejects_negative_balance():
    service = DefaultMemberService(MemberRepository())
    pending = {"account_type": "savings", "new_balance": "-1.00"}

    try:
        service.handle_balance_update("M001", "confirm", pending)
    except ValueError as exc:
        assert str(exc) == "New balance cannot be negative."
    else:
        raise AssertionError("Expected negative balance to be rejected")


def test_member_service_rejects_unknown_account():
    service = DefaultMemberService(MemberRepository())
    pending = {"account_type": "unknown", "new_balance": "100.00"}

    try:
        service.handle_balance_update("M001", "confirm", pending)
    except ValueError as exc:
        assert "Account 'unknown' not found" in str(exc)
    else:
        raise AssertionError("Expected unknown account to be rejected")
