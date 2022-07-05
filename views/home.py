from ast import Return
from asyncio import events
import os
from random import randint
import re
from flask import (
    Blueprint,
    abort,
    session,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from auth import User
from contract import Contract
from app import owner, w3


home = Blueprint("home", __name__)
# get all colletibles from static folder
images = [
    image for image in os.listdir("./static/images/collectibles")
]
# initialize collectibles list to be showed in the home page
collectibles = images

# Route per the home page
# If the user is logged and the contracts deployed, it will show a list of collectibles ready to be minted
# The page displays the account and the balance in the case of a logged user
@home.route("/", methods=["GET", "POST"])
def index():
    # if logged, show the balance and the account
    if current_user.is_authenticated and Contract.CONTRACTS_DEPLOYED == True:
        balance = Contract.nft_instance.functions.balanceOf(current_user.id).call()
    else:
         balance = 0
    # if logged and subscribed to the lottery, calculate notifications to display the number of new events
    if current_user.is_authenticated and session['subscribed'] == True:
        # this function updates the session with the new events
        calculate_notifications()
        notifications_count = len(session['events'])
    else:
        # if not subscribed to the lottery, set the notifications count to 0
        session['events'] = []
        notifications_count = 0

    # make a list only with the collectibles that have not already been collected to avoid double minting
    # i.e. with owner = 0x0000000000000000000000000000000000000000
    collectibles_free = []
    # if the contracts have not been deployed, show the home page without the collectibles to be minted
    if not Contract.CONTRACTS_DEPLOYED:
        return render_template("index2.html", user = current_user, collectibles=collectibles_free, balance=balance, notifications_count=0)
    # else show the available collectibles
    for collectible in collectibles:
        curr_id = int(collectible.replace(".jpg", ""))
        if Contract.nft_instance.functions.ownerOf(curr_id).call() == "0x0000000000000000000000000000000000000000":
            collectibles_free.append(collectible)
    
    return render_template("index2.html", user = current_user, collectibles=collectibles_free, balance = balance, notifications_count= notifications_count)

# Route for mint a collectible
@home.route("/mint", methods=["POST"])
@login_required
def mint(): 
    # if the route is accedeed from the url, flash an error message 
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    # get the collectible id from the form
    collectible = request.form.get("collectible")
    id = int(collectible.replace(".jpg", ""))
    # check if the collectible corresponding to this id, has not an owner
    # if not so, transaction is sent to the blockchain
    if Contract.nft_instance.functions.ownerOf(id).call() == "0x0000000000000000000000000000000000000000":
        if current_user.role == "USER":
            try:
                tx = {
                    "from": current_user.id,
                    "to": Contract.nft_address,
                    "gas": 2000000,
                    "gasPrice": w3.toWei("40", "gwei"),
                }
                # if the user is not the lottery manager, it will be sent to the contract ERC721 and the token
                # will be minted without assigning the class prize
                tx_hash = Contract.nft_instance.functions.createToken(int(id), collectible).transact(
                    tx
                )
                bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                
            except Exception as e:
                flash(f"Error: {e['message']}", "danger")
        # if the user is the lottery manager, the transaction is called from the lottery smart contract in
        # order to set this collectible as a future prize for the lottery
        if current_user.role == "MANAGER":
            try:
                tx = {
                    "from": owner.address,
                    "to": Contract.lottery_address,
                    "gas": 2000000,
                    "gasPrice": w3.toWei("40", "gwei"),
                }
                #  the random class prize is calculated directly in the smart contract
                tx_hash = Contract.lottery_instance.functions.buyCollectibles(collectible, id).transact(
                    tx
                )
                bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                status = bid_txn_receipt.status
                isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
                if status != 1:
                    if bid_txn_receipt.get("from") != owner.address:
                        error_msg = "You are not the owner"
                    if isLotteryActive == False:
                        error_msg = "The lottery is not active" 
            except Exception as e:
                flash(f"Error: {e['message']}", "danger")
        flash("Collectible minted successfully", "success")
        collectibles.remove(collectible)
    else:
        flash("This collectible is already owned", "danger")
    return redirect(url_for("home.index"))

# Route for the lottery page
# different from user and manager
@home.route("/lottery", methods=["GET", "POST"])
@login_required
def lottery():
    # initialize the variables to be used in the template that make changes
    isLotteryActive = False
    isRoundActive = False
    prizes = False

    # if the contract has been deployed, call the function in the smart contract and use the real values
    # else, use the previous values initialized at false
    if Contract.CONTRACTS_DEPLOYED:
        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()  
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call() 

    # error message initializing 
    # it will be used to communicate why the transaction has failed
    error_msg = ""

    if request.method == "GET":
        # if the user is the manager, use the variables to display the buttons to start the lottery or the round or to manage the lottery operations
        if(current_user.role == 'MANAGER'):
            # notifications are not displayed in case of lottery manager
            return render_template("lottery_manager.html", user = current_user, prizes = prizes, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, error = error_msg, notifications_count = 0)
        # if the user is a normal user, use the variables to display an error message to wait for the lottery start, or the template
        # to buy a ticket
        if(current_user.role == 'USER'):
            # this variable is used to display a button to subscribe to the lottery if a user is not subscribed and play
            subscribed = session['subscribed']
            if(subscribed == True) and Contract.CONTRACTS_DEPLOYED:
                # if the user is subscribed and contracts deployed, calculate notifications
                calculate_notifications()
                notifications_count = len(session.get('events', []))
            else:
                notifications_count = 0
            return render_template("lottery_user.html", user = current_user, isRoundActive=isRoundActive, error = error_msg, subscribed = subscribed, notifications_count = notifications_count)

    # The post method is used only in case the user will buy a ticket
    if request.method == "POST":
        if not Contract.CONTRACTS_DEPLOYED:
            flash("Contracts not deployed yet", "danger")
            return redirect(url_for("home.index"))

        # the number of notification is updated
        calculate_notifications()
        notifications_count = len(session['events'])

        # take numbers played in the form
        first_number = int(request.form.get("firstnumber"))
        second_number = int(request.form.get("secondnumber"))
        third_number = int(request.form.get("thirdnumber"))
        fourth_number = int(request.form.get("fourthnumber"))
        fifth_number = int(request.form.get("fifthnumber"))
        powerball_number = int(request.form.get("powerballnumber"))
        # if the numbers are valid, use them for the transaction
        # eventual errors of ranges of numbers, strings ecc. will be displayed in the form without sending the transaction
        # other errors will be managed by the return status of the transaction, for example same number played twice
        try:
            wei = w3.toWei(10, "gwei")
            tx = {
                "from": current_user.id,
                "to": Contract.lottery_address,
                "value": wei,
                "gas": 2000000,
                "gasPrice": w3.toWei("40", "gwei"),
            }
            tx_hash = Contract.lottery_instance.functions.buyTicket(first_number, second_number, third_number, fourth_number, fifth_number, powerball_number).transact(
                tx
            )
            bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            status = bid_txn_receipt.status

            # if the transaction fails, check the errors in the transaction requirements, and update the variable for the error message
            if status != 1:
            # raise an error if the transaction failed
                if Contract.lottery_instance.functions.isRoundActive().call() == False:
                    error_msg = "The round is not active"
                if Contract.lottery_instance.functions.isLotteryActive().call() == False:
                    error_msg = "The lottery is not active"  
                if ((first_number != second_number and first_number != third_number and first_number != fourth_number and first_number != fifth_number and second_number != third_number and second_number != fourth_number and second_number != fifth_number and third_number != fourth_number and third_number != fifth_number) and (first_number != powerball_number and second_number != powerball_number and third_number != powerball_number and fourth_number != powerball_number and fifth_number != powerball_number)) == False:
                    error_msg = "The numbers must be different"
        except Exception as e:
            flash(f"Error: {e['message']}", "danger")

    return render_template("lottery_user.html",  user = current_user, isRoundActive=isRoundActive, error = error_msg, subscribed = session['subscribed'], notifications_count=notifications_count)

# Route for the user subscription to the lottery
@home.route("/lottery/subscribe", methods=["GET"])
@login_required
def lottery_subscribe():
    # when a user subscribes to the lottery, the session subscribed boolean value is se to true, in order to make
    # the user play lottery and receive notifications
    session['subscribed'] = True
    # list of notifications initialized to empty
    session['events'] = []
    # this is the number of the block in which the user subscribed to the lottery in order to show only the notifications that 
    # are related to blocks subsequent to the user subscription
    session['start_notifications'] = w3.eth.blockNumber

    return redirect(url_for(".lottery"))

# Route for the manager to start the lottery and deploy the contracts
@home.route("/lottery/start", methods = ["GET"])
@login_required
def start_lottery():
    # If the contract has already been deployed, the manager can't start the lottery again
    if Contract.CONTRACTS_DEPLOYED:
        flash("Contracts already deployed", "danger")
        return redirect(url_for(".lottery")) 
    # call the function to deploy the contracts and update the variables
    Contract.deploy_lottery()

    error_msg = ""
    isRoundActive = Contract.lottery_instance.functions.isRoundActive().call() 
    # if the user is the manager, the lottery started enable the showing of the "round start" button
    # the transaction will set the lottery to active
    if current_user.role == 'MANAGER':
        try:
            wei = w3.toWei(10, "gwei")
            tx = {
                "from": owner.address,
                "to": Contract.lottery_address,
                "gas": 2000000,
                "gasPrice": w3.toWei("40", "gwei"),
            }
            tx_hash = Contract.lottery_instance.functions.createLottery().transact(
                tx
            )
            bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            status = bid_txn_receipt.status
            if status != 1:
                if Contract.lottery_instance.functions.isLotteryActive().call() == True:
                    error_msg = "The lottery is already active"
        except Exception as e:
            flash(f"Error: {e['message']}", "danger")
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call()
        return render_template("lottery_manager.html",  user = current_user, error = error_msg, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, prizes = prizes,notifications_count = 0)
   
# Route for the manager to start the round
@home.route("/lottery/round", methods=["GET"])
@login_required
def lottery_round():
    # if the contract has not been deployed, the manager can't start the round
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    error_msg = ""
    if current_user.role == 'MANAGER':
        # active the round in the lottery contract calling the transaction to open a round and set all the varibales
        try:
            wei = w3.toWei(10, "ether")
            tx = {
                "from": owner.address,
                "to": Contract.lottery_address,
                "gas": 2000000,
                "gasPrice": w3.toWei("40", "gwei"),
            }
            tx_hash = Contract.lottery_instance.functions.newRound().transact(
                tx
            )
            bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            status = bid_txn_receipt.status
            # check, if the status of the transaction means failure, the requirements of the trasnaction
            # in order to find the reason of failure and display the error message
            if status != 1:
                # raise an error if the transaction failed
                if Contract.lottery_instance.functions.isLotteryActive().call() == False:
                    error_msg = "The lottery is not active"
                if bid_txn_receipt.get("from") != owner.address:
                    error_msg = "You are not the owner"
                if Contract.lottery_instance.functions.isRoundActive().call() == True:
                    error_msg = "The round is already active"
                if Contract.lottery_instance.functions.prizesAssigned().call() == False:
                    error_msg = "The prizes are not assigned, the previous round is not finished"
        except Exception as e:
            flash(f"Error: {e['message']}", "danger")

        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()       
        return render_template("lottery_manager.html", user = current_user, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, error = error_msg, notifications_count = 0)

# Route for the manager to close the lottery and reset the variables
@home.route("/lottery/destroylottery", methods=["GET"])
@login_required
def destroy_lottery():
    # this function can be called only if the contract has been deployed
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    error_msg = ""
    if current_user.role == 'MANAGER':
        # destroy the lottery contract calling the contract function to destroy the lottery and set the variables
        try:
            wei = w3.toWei(10, "ether")
            tx = {
                "from": owner.address,
                "to": Contract.lottery_address,
                "gas": 2000000,
                "gasPrice": w3.toWei("40", "gwei"),
            }
            tx_hash = Contract.lottery_instance.functions.destroyLottery().transact(
                tx
            )
            bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            status = bid_txn_receipt.status
            isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
            if status != 1:
                # raise an error if the transaction failed
                if bid_txn_receipt.get("from") != owner.address:
                    error_msg = "You are not the owner"
                if isLotteryActive == False:
                    error_msg = "The lottery is not active"
            else: 
                Contract.CONTRACTS_DEPLOYED = False
                flash("Lottery destroyed", "success")
        except Exception as e:
            flash(f"Error: {e['message']}", "danger")
        return redirect(url_for(".lottery"))
      
# Rout for the manager to draw numbers
@home.route("/lottery/drawnumbers", methods=["GET"])
@login_required
def draw_numbers():
    # this function can be called only if the contract has been deployed
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))

    # initialize the variable for the error message
    error_msg = ""
    if current_user.role == 'MANAGER':
        # call the function to draw the numbers
        try:
            wei = w3.toWei(10, "ether")
            tx = {
                "from": owner.address,
                "to": Contract.lottery_address,
                "gas": 2000000,
                "gasPrice": w3.toWei("40", "gwei"),
            }
            tx_hash = Contract.lottery_instance.functions.drawNumbers().transact(
                tx
            )
            bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            status = bid_txn_receipt.status
            # check, if the status of the transaction means failure, the requirements of the trasnaction
            if status != 1:
                block_number = bid_txn_receipt.get("blockNumber")
                end = Contract.lottery_instance.functions.end().call()
                k = Contract.lottery_instance.functions.K().call()
                if block_number < end:
                    error_msg = "The round is not finished"
                # for this particular requirement the error message is not clear: the blockchain is local, so 
                # we have to perform K more transaction after the round ending to draw numbers and guarantee
                # the unpredictability of the numbers drawn
                if (block_number <= end + k):
                    error_msg = "The numbers will be drawn after some transactions"
                if bid_txn_receipt.get("from") != owner.address:
                    error_msg = "You are not the owner"
                if Contract.lottery_instance.functions.isRoundActive().call() == True:
                    error_msg = "The round is already active"
                if Contract.lottery_instance.functions.prizesAssigned().call() == True:
                    error_msg = "The prizes are already assigned and the round is already finished"
                if Contract.lottery_instance.functions.isLotteryActive().call() == False:
                    error_msg = "The lottery is not active"
                winner = Contract.lottery_instance.functions.winner().call()
                if winner[6] != 0:
                    error_msg = "The numbers have already been drawn"
        except Exception as e:
            flash(f"Error: {e['message']}", "danger")
        # update the variables for the page
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call()
        return render_template("lottery_manager.html",  user = current_user, error = error_msg, prizes = prizes, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, notifications_count = 0)

# Route for the manager to assign the prizes
@home.route("/lottery/assignprizes", methods=["GET"])
@login_required
def assign_prizes():
    # this function can be called only if the contract has been deployed
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    # initialize the variable for the error message
    error_msg = ""
    if current_user.role == 'MANAGER':
        # assign the prizes calling the function from the contract
        try:
            tx = {
                "from": owner.address,
                "to": Contract.lottery_address,
                "gas": 2000000,
                "gasPrice": w3.toWei("40", "gwei"),
            }
            tx_hash = Contract.lottery_instance.functions.givePrizes().transact(
                tx
            )
            bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            status = bid_txn_receipt.status
            # check, if the status of the transaction means failure, the requirements of the trasnaction
            if status != 1:               
                if bid_txn_receipt.get("from") != owner.address:
                    error_msg = "You are not the owner"
                if Contract.lottery_instance.functions.isRoundActive().call() == True:
                    error_msg = "The round is already active"
                if Contract.lottery_instance.functions.prizesAssigned().call() == True:
                    error_msg = "The prizes are already assigned and the round is already finished"
                if Contract.lottery_instance.functions.isLotteryActive().call() == False:
                    error_msg = "The lottery is not active"
            
                winner = Contract.lottery_instance.functions.winner().call()
                if winner[6] == 0:
                    error_msg = "The numbers have not been drawn"
                
        except Exception as e:
            flash(f"Error: {e['message']}", "danger")
        # update the variables for the page
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call()
        return render_template("lottery_manager.html",  user = current_user, error = error_msg, prizes = prizes, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, notifications_count = 0)

# Function to update the session variables for the lottery notifications and the notifications count
def calculate_notifications():
    # if the contract has not been deployed yet, return and clean the session events 
    if not Contract.CONTRACTS_DEPLOYED:
        session['events'] = []
        return
    
    # instantiate the events to be listened on the blockchain
    events_entries = (
            Contract.lottery_start_event.get_all_entries()
            + Contract.lottery_close_event.get_all_entries()
            + Contract.draw_numbers_event.get_all_entries()
            + Contract.prizes_assigned_event.get_all_entries()
            + Contract.round_start_event.get_all_entries()
        )
    
    # Events entries ordered from the oldest to the newest
    events_entries.sort(key=lambda x: x.blockNumber, reverse=True)

    # for each event take the event name and the arguments (i.e. numbers drawn)
    for e in events_entries:
        block_id = e.blockNumber
        event = e.event
        args = e.args
        # Show the notification only if the block number of the event is more recent then the 
        # block number in which the user subscribed to the lottery
        if block_id <= session['start_notifications'] or event == "mintToken":
            continue

        block_id = str(e.blockNumber)
        # Check if the event is already notified, if not so, initialize the list empty
        if not session.get(block_id):
            session[block_id] = []

        # Distinguish event in order to make a clear message with arguments only if needed
        if event == "assignPrize":
            # if the event is assign prize, we have to check also the arguments because the prize assigned can be 
            # more than one and if we check only the name of the event, we notify only one prize assignment
            if (event, args.get('id')) not in session.get(block_id):
                session[block_id].append((event,args.get('id')))
                session['events'].append("Prize Assigned")
        # other events are notified only with the name of the event except for numbers drawing because an user
        # has to know the winning numbers
        else:
            if event not in session.get(block_id):
                session[block_id].append((event))
                if event == "lotteryStart":
                    session['events'].append("Lottery Started")
                elif event == "closeLottery":
                    session['events'].append("Lottery Closed")
                elif event == "roundStart":
                    session['events'].append("Round Started")
                elif event == "drawing":
                    session['events'].append("Numbers Drawn: "+str(args.get('firstNumber'))+ ", " + str(args.get("secondNumber")) + ", " + str(args.get("thirdNumber")) + ", " + str(args.get("fourthNumber")) + ", " + str(args.get("fifthNumber")) + ", " + str(args.get("powerballNumber")))
               
# Route for users to show the notifications
@home.route("/notifications", methods=["GET"])
@login_required
def notifications():
    # function can be called only if the contract has been deployed
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    if request.method == "GET":
        # calculate notifications only if the user is subscribed to the lottery
        if session['subscribed'] == True:
            calculate_notifications()
            return render_template("notifications.html", user = current_user, events=(session['events'][::-1]), subscribed = session['subscribed'], notifications_count = len(session['events']))
        # else show an empty page
        else:
            return render_template("notifications.html", events = [], user = current_user, subscribed = session['subscribed'], notifications_count = 0)

# Route for users to clean the page of notifications
@home.route("/notifications/deleteall", methods=["GET"])  
@login_required
def delete_all_notifications():
    # function can be called only if the contract has been deployed
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    if request.method == "GET":
        # the variables are cleaned
        session['events'] = []
        return render_template("notifications.html", events = [], user = current_user, subscribed = session['subscribed'], notifications_count = 0)