"""
Application entry point.

This file is intentionally thin and only wires together the layers.
- create Flask app
- init database
- register controller blueprint
"""

from flask import Flask

from target_app.database import init_db
from target_app.controllers.member_controller import member_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "demo-banking-app-secret-key"

    init_db()
    app.register_blueprint(member_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
