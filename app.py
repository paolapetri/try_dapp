from flask_executor import Executor
import json

from web3 import Web3, HTTPProvider
from flask import Flask


# create a web3.py instance w3 by connecting to the local Ethereum node
w3 = Web3(HTTPProvider("http://localhost:8545"))
# Initialize a local account object from the private key of a valid Ethereum node address
owner = w3.eth.account.from_key("0x4bd11ba33fe8e743830a70b79bf676b44d74a26834e926001b3b36b0a687afda")


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
