"""
Flask Routes (Controllers) - Handle HTTP requests.

This file ONLY:
- Accepts HTTP requests
- Calls database layer to get data
- Returns responses (HTML or JSON)

No database queries here! We call database.py functions.
"""

from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify

# Import database functions
from target_app.database import (
    find_member_by_id,
    search_members,
    get_member_accounts,
    get_member_transactions,
)

# Create blueprint for routes
routes_bp = Blueprint('routes', __name__)


# ============ HOME PAGE ============

@routes_bp.route("/")
def index():
    """Home page."""
    return render_template("index.html")


# ============ MEMBER SEARCH ============

@routes_bp.route("/members/search", methods=["GET", "POST"])
def search_members_page():
    """Search for members."""
    results = None
    search_term = None
    error = None
    
    if request.method == "POST":
        search_term = request.form.get("member_id_or_name", "").strip()
        
        if not search_term:
            error = "Please enter a member ID or name"
        else:
            # Call database layer
            results = search_members(search_term)
            
            if not results:
                error = f"No members found matching '{search_term}'"
            else:
                session["last_search"] = search_term
    
    return render_template(
        "search.html",
        results=results,
        search_term=search_term,
        error=error
    )


# ============ MEMBER DETAIL ============

@routes_bp.route("/members/<member_id>/detail")
def member_detail(member_id):
    """Show member details."""
    # Call database layer
    member = find_member_by_id(member_id)
    
    if not member:
        return redirect(url_for('routes.search_members_page'))
    
    # Call database layer
    accounts = get_member_accounts(member_id)
    transactions = get_member_transactions(member_id, limit=5)
    
    return render_template(
        "member_detail.html",
        member=member,
        accounts=accounts,
        transactions=transactions
    )


# ============ UPDATE BALANCE FORM ============

@routes_bp.route("/members/<member_id>/update-balance", methods=["GET", "POST"])
def update_balance(member_id):
    """Show update balance form."""
    # Call database layer
    member = find_member_by_id(member_id)
    
    if not member:
        return redirect(url_for('routes.search_members_page'))
    
    # Call database layer
    accounts = get_member_accounts(member_id)
    
    if request.method == "POST":
        account_type = request.form.get("account_type")
        new_balance = request.form.get("new_balance")
        notes = request.form.get("notes", "")
        
        # Store in session for next step
        session["pending_update"] = {
            "member_id": member_id,
            "account_type": account_type,
            "new_balance": new_balance,
            "notes": notes,
        }
        
        return redirect(url_for('routes.confirm_update', member_id=member_id))
    
    return render_template(
        "update_balance.html",
        member=member,
        accounts=accounts
    )


# ============ CONFIRM UPDATE ============

@routes_bp.route("/members/<member_id>/confirm-update", methods=["GET", "POST"])
def confirm_update(member_id):
    """Confirmation page for update."""
    # Call database layer
    member = find_member_by_id(member_id)
    
    if not member:
        return redirect(url_for('routes.search_members_page'))
    
    pending = session.get("pending_update")
    
    if not pending:
        return redirect(url_for('routes.update_balance', member_id=member_id))
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "confirm":
            from datetime import datetime
            result = {
                "success": True,
                "message": f"Balance updated successfully for {member.name}",
                "updated_at": datetime.now().isoformat(),
                "account_type": pending["account_type"],
                "new_balance": pending["new_balance"]
            }
            session.pop("pending_update", None)
            session["last_result"] = result
            return redirect(url_for('routes.update_result', member_id=member_id))
        
        elif action == "cancel":
            session.pop("pending_update", None)
            return redirect(url_for('routes.member_detail', member_id=member_id))
    
    return render_template(
        "confirm_update.html",
        member=member,
        pending=pending
    )


# ============ RESULT PAGE ============

@routes_bp.route("/members/<member_id>/result")
def update_result(member_id):
    """Result page after update."""
    # Call database layer
    member = find_member_by_id(member_id)
    
    if not member:
        return redirect(url_for('routes.search_members_page'))
    
    result = session.get("last_result")
    
    if not result:
        return redirect(url_for('routes.member_detail', member_id=member_id))
    
    return render_template(
        "result.html",
        member=member,
        result=result
    )


# ============ API ENDPOINTS ============

@routes_bp.route("/api/member/<member_id>")
def api_member(member_id):
    """API endpoint to get member data."""
    # Call database layer
    member = find_member_by_id(member_id)
    
    if not member:
        return jsonify({"error": "Member not found"}), 404
    
    # Call database layer
    accounts = get_member_accounts(member_id)
    
    return jsonify({
        "member": member.__dict__(),
        "accounts": [acc.__dict__() for acc in accounts]
    })


@routes_bp.route("/health")
def health():
    """Health check."""
    from datetime import datetime
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})
