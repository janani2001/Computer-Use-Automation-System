"""Integration tests for safe balance-update system failures."""

from target_app.app import create_app


def test_balance_update_system_failure_returns_safe_500_screen_without_clearing_pending_update():
    app = create_app()
    app.config.update(TESTING=True, SIMULATE_BALANCE_UPDATE_FAILURE=True)
    client = app.test_client()

    with client.session_transaction() as current_session:
        current_session["pending_update"] = {
            "member_id": "M001",
            "account_type": "savings",
            "new_balance": "13000.00",
            "notes": "Approved test update",
        }

    response = client.post(
        "/members/M001/confirm-update",
        data={"action": "confirm"},
    )

    assert response.status_code == 500
    assert b"Balance Update Unavailable" in response.data
    assert b"No confirmation was recorded" in response.data
    assert b"Traceback" not in response.data

    with client.session_transaction() as current_session:
        assert current_session["pending_update"]["new_balance"] == "13000.00"
        assert "last_result" not in current_session
