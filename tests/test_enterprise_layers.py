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
