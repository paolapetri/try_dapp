from app import w3, owner
import json

class Contract:
    CONTRACTS_DEPLOYED = False

    nft_address = None
    nft_instance = None
    lottery_address = None
    lottery_instance = None

    lottery_start_event = None
    mint_event = None
    round_start_event = None
    token_minted = None
    lottery_close_event = None
    draw_numbers_event = None
    prizes_assigned_event = None
    
    @staticmethod
    def deploy_lottery():

        # DEPLOY NFT ERC 721 CONTRACT
        truffle_file = json.load(open("./build/contracts/NFT_ERC721.json"))
        abi = truffle_file["abi"]
        bytecode = truffle_file["bytecode"]

        # Initialize a contract object with the smart contract compiled artifacts
        contract = w3.eth.contract(bytecode=bytecode, abi=abi)

        # build a transaction by invoking the buildTransaction() method from the smart contract constructor function
        construct_txn = contract.constructor().buildTransaction(
            {
                "from": owner.address,
                "nonce": w3.eth.getTransactionCount(owner.address),
                "gas": 30000000,
                "gasPrice": w3.toWei("21", "gwei"),
            }
        )

        # sign the deployment transaction with the private key
        signed = w3.eth.account.sign_transaction(construct_txn, owner.key)

        # broadcast the signed transaction to your local network using sendRawTransaction() method and get the transaction hash
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)

        # collect the Transaction Receipt with contract address when the transaction is mined on the network
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        Contract.nft_address = tx_receipt["contractAddress"]

        # Initialize a contract instance object using the contract address which can be used to invoke contract functions
        Contract.nft_instance = w3.eth.contract(abi=abi, address=Contract.nft_address)

        truffle_file = json.load(open("./build/contracts/NFT_Lottery.json"))
        abi = truffle_file["abi"]
        bytecode = truffle_file["bytecode"]

        # Initialize a contract object with the smart contract compiled artifacts
        contract = w3.eth.contract(bytecode=bytecode, abi=abi)

        # build a transaction by invoking the buildTransaction() method from the smart contract constructor function
        construct_txn = contract.constructor(Contract.nft_address, 3).buildTransaction(
            {
                "from": owner.address,
                "nonce": w3.eth.getTransactionCount(owner.address),
                "gas": 30000000,
                "gasPrice": w3.toWei("21", "gwei"),
            }
        )

        # sign the deployment transaction with the private key
        signed = w3.eth.account.sign_transaction(construct_txn, owner.key)

        # broadcast the signed transaction to your local network using sendRawTransaction() method and get the transaction hash
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)

        # collect the Transaction Receipt with contract address when the transaction is mined on the network
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        Contract.lottery_address = tx_receipt["contractAddress"]

        # Initialize a contract instance object using the contract address which can be used to invoke contract functions
        Contract.lottery_instance = w3.eth.contract(abi=abi, address=Contract.lottery_address)

        Contract.lottery_start_event = (Contract.lottery_instance.events.lotteryStart.createFilter(fromBlock=1, toBlock="latest"))
        Contract.round_start_event = (Contract.lottery_instance.events.roundStart.createFilter(fromBlock=1, toBlock="latest"))
        Contract.lottery_close_event = (Contract.lottery_instance.events.closeLottery.createFilter(fromBlock=1, toBlock="latest"))
        Contract.draw_numbers_event = (Contract.lottery_instance.events.drawing.createFilter(fromBlock=1, toBlock="latest"))
        Contract.prizes_assigned_event = (Contract.lottery_instance.events.assignPrize.createFilter(fromBlock=1, toBlock="latest"))
        Contract.mint_event = (Contract.lottery_instance.events.mintToken.createFilter(fromBlock=1, toBlock="latest"))
        Contract.CONTRACTS_DEPLOYED = True
