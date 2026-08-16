"""Thin HTTP controller layer.

Each resource (URL) is one MethodView class. Flask dispatches to `get`/`post`
based on the incoming HTTP verb, so there is exactly one route registration
per URL and no request.method branching anywhere in this file.
"""

from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from flask.views import MethodView

from target_app.repositories.member_repository import MemberRepository
from target_app.services.member_service import DefaultMemberService, MemberService

member_bp = Blueprint("member_bp", __name__)
member_service: MemberService = DefaultMemberService(MemberRepository())


class IndexView(MethodView):
    def get(self):
        return render_template("index.html")


class MemberSearchView(MethodView):
    def get(self):
        return render_template("search.html", results=[], search_term="", error=None)

    def post(self):
        search_term = request.form.get("member_id_or_name", "")
        result = member_service.search_members(search_term)

        if result["error"] is None:
            session["last_search"] = result["search_term"]

        return render_template(
            "search.html",
            results=result["results"],
            search_term=result["search_term"],
            error=result["error"],
        )


class MemberDetailView(MethodView):
    def get(self, member_id):
        detail = member_service.get_member_detail(member_id)
        if not detail:
            return redirect(url_for("member_bp.search_members"))

        return render_template(
            "member_detail.html",
            member=detail["member"],
            accounts=detail["accounts"],
            transactions=detail["transactions"],
        )


class UpdateBalanceView(MethodView):
    def get(self, member_id):
        context = member_service.prepare_update_context(member_id)
        if not context:
            return redirect(url_for("member_bp.search_members"))

        return render_template("update_balance.html", member=context["member"], accounts=context["accounts"])

    def post(self, member_id):
        context = member_service.prepare_update_context(member_id)
        if not context:
            return redirect(url_for("member_bp.search_members"))

        session["pending_update"] = {
            "member_id": member_id,
            "account_type": request.form.get("account_type"),
            "new_balance": request.form.get("new_balance"),
            "notes": request.form.get("notes", ""),
            "timestamp": datetime.now().isoformat(),
        }
        return redirect(url_for("member_bp.confirm_update", member_id=member_id))


class ConfirmUpdateView(MethodView):
    def get(self, member_id):
        detail = member_service.get_member_detail(member_id)
        if not detail:
            return redirect(url_for("member_bp.search_members"))

        pending = session.get("pending_update")
        if not pending:
            return redirect(url_for("member_bp.update_balance", member_id=member_id))

        return render_template("confirm_update.html", member=detail["member"], pending=pending)

    def post(self, member_id):
        detail = member_service.get_member_detail(member_id)
        if not detail:
            return redirect(url_for("member_bp.search_members"))

        pending = session.get("pending_update")
        if not pending:
            return redirect(url_for("member_bp.update_balance", member_id=member_id))

        action = request.form.get("action")
        decision = member_service.handle_balance_update(member_id, action, pending)

        if decision["status"] == "cancelled":
            session.pop("pending_update", None)
            return redirect(url_for("member_bp.member_detail", member_id=member_id))

        session.pop("pending_update", None)
        session["last_result"] = decision["result"]
        return redirect(url_for("member_bp.update_result", member_id=member_id))


class UpdateResultView(MethodView):
    def get(self, member_id):
        detail = member_service.get_member_detail(member_id)
        if not detail:
            return redirect(url_for("member_bp.search_members"))

        result = session.get("last_result")
        if not result:
            return redirect(url_for("member_bp.member_detail", member_id=member_id))

        return render_template("result.html", member=detail["member"], result=result)


class ApiMemberView(MethodView):
    def get(self, member_id):
        detail = member_service.get_member_detail(member_id)
        if not detail:
            return jsonify({"error": "Member not found"}), 404

        return jsonify({
            "member": detail["member"].__dict__(),
            "accounts": [account.__dict__() for account in detail["accounts"]],
        })


class HealthView(MethodView):
    def get(self):
        return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


member_bp.add_url_rule("/", view_func=IndexView.as_view("index"))
member_bp.add_url_rule("/members/search", view_func=MemberSearchView.as_view("search_members"))
member_bp.add_url_rule("/members/<member_id>/detail", view_func=MemberDetailView.as_view("member_detail"))
member_bp.add_url_rule("/members/<member_id>/update-balance", view_func=UpdateBalanceView.as_view("update_balance"))
member_bp.add_url_rule("/members/<member_id>/confirm-update", view_func=ConfirmUpdateView.as_view("confirm_update"))
member_bp.add_url_rule("/members/<member_id>/result", view_func=UpdateResultView.as_view("update_result"))
member_bp.add_url_rule("/api/member/<member_id>", view_func=ApiMemberView.as_view("api_member"))
member_bp.add_url_rule("/health", view_func=HealthView.as_view("health"))

