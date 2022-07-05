from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    session,
    request,
    session,
    url_for,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import w3, owner
from views.home import calculate_notifications, notifications
from auth import User

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", user = current_user, accounts = w3.eth.accounts, notifications_count = 0)
    address = request.form.get("account")
    if not address:
        abort(400)
    if w3.isAddress(address):
        session['address'] = address
        session['subscribed'] = False
        flash("Successfully authenticated", "success")
        u = User(address, 'USER' if address != owner.address else 'MANAGER')
        login_user(u)
        return redirect(url_for("home.index"))
    else:
        flash("Invalid address", "danger")
        return render_template("login.html", user = current_user, accounts = w3.eth.accounts, notifications_count = 0)
    
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return render_template("login.html", user = current_user, accounts = w3.eth.accounts , notifications_count = 0)