from flask_executor import Executor
import json

from web3 import Web3, HTTPProvider
from flask import Flask


# create a web3.py instance w3 by connecting to the local Ethereum node
w3 = Web3(HTTPProvider("http://localhost:8545"))

# ------------------------------------------------INSERT PRIVATE KEY OF LOTTERY MANAGER HERE------------------------------------------------------------
owner = w3.eth.account.from_key("0xd22de7f99104560e88989244284429fccfe73ae2a5acc44014bead3dc76179af")


executor = Executor() 
def create_app():
    from views.home import home
    from views.auth import auth
    import auth as lm
    app = Flask(__name__)
    app.config['ENV'] = "development"
    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = "supersecret"

    app.register_blueprint(home)
    app.register_blueprint(auth)
    lm.init_login_manager(app)
    
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    app.run(debug=True)
