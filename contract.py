from app import w3, owner
import json
"""
Contract class to interact with the contract and deploy the contract on demand 
It contains also the variables to initialize init filters
"""
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

        # Deploy ERC721 contract
        truffle_file = json.load(open("./build/contracts/NFT_ERC721.json"))
        abi = truffle_file["abi"]
        bytecode = truffle_file["bytecode"]

        contract = w3.eth.contract(bytecode=bytecode, abi=abi)
        construct_txn = contract.constructor().buildTransaction(
            {
                "from": owner.address,
                "nonce": w3.eth.getTransactionCount(owner.address),
                "gas": 30000000,
                "gasPrice": w3.toWei("21", "gwei"),
            }
        )
        signed = w3.eth.account.sign_transaction(construct_txn, owner.key)

        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)

        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        Contract.nft_address = tx_receipt["contractAddress"]

        Contract.nft_instance = w3.eth.contract(abi=abi, address=Contract.nft_address)


        # Deploy lottery contract
        truffle_file = json.load(open("./build/contracts/NFT_Lottery.json"))
        abi = truffle_file["abi"]
        bytecode = truffle_file["bytecode"]

        contract = w3.eth.contract(bytecode=bytecode, abi=abi)

        construct_txn = contract.constructor(Contract.nft_address, 3).buildTransaction(
            {
                "from": owner.address,
                "nonce": w3.eth.getTransactionCount(owner.address),
                "gas": 30000000,
                "gasPrice": w3.toWei("21", "gwei"),
            }
        )

        signed = w3.eth.account.sign_transaction(construct_txn, owner.key)
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)

        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        Contract.lottery_address = tx_receipt["contractAddress"]

        Contract.lottery_instance = w3.eth.contract(abi=abi, address=Contract.lottery_address)

        # init event filters to listen for events on the blockchain and communicate notifications
        Contract.lottery_start_event = (Contract.lottery_instance.events.lotteryStart.createFilter(fromBlock=1, toBlock="latest"))
        Contract.round_start_event = (Contract.lottery_instance.events.roundStart.createFilter(fromBlock=1, toBlock="latest"))
        Contract.lottery_close_event = (Contract.lottery_instance.events.closeLottery.createFilter(fromBlock=1, toBlock="latest"))
        Contract.draw_numbers_event = (Contract.lottery_instance.events.drawing.createFilter(fromBlock=1, toBlock="latest"))
        Contract.prizes_assigned_event = (Contract.lottery_instance.events.assignPrize.createFilter(fromBlock=1, toBlock="latest"))
        Contract.mint_event = (Contract.lottery_instance.events.mintToken.createFilter(fromBlock=1, toBlock="latest"))
        # Variable to check if the contracts have been deployed or not
        Contract.CONTRACTS_DEPLOYED = True
