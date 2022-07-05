from flask_login import UserMixin, LoginManager
from app import w3, owner

"""
Lightweight class for representing a user.
"""
class User(UserMixin):
    
    def __init__(self, address: str, role: str):
        self.id = address
        self.role = role
    
    def __repr__(self):
        return f"User({self.id}, {self.role})"

def init_login_manager(app):
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = u"Please login to perform this operation."

    @login_manager.user_loader
    def load_user(user_id):
        """
        :param user_id: The address of the user to search for in w3 accounts
        :return: the user object
        """
        # Return a User object searching in w3 accounts by address
        accounts = w3.eth.accounts
        for account in accounts:
            if account == user_id:
                return User(account, 'USER' if account != owner.address else 'MANAGER')

    return login_manager
    