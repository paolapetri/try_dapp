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
collectibles = images
@home.route("/", methods=["GET", "POST"])
def index():
    # if logged
    if current_user.is_authenticated and Contract.CONTRACTS_DEPLOYED == True:
        balance = Contract.nft_instance.functions.balanceOf(current_user.id).call()
    else:
         balance = 0
    if current_user.is_authenticated and session['subscribed'] == True:
        calculate_notifications()
        notifications_count = len(session['events'])
    else:
        session['events'] = []
        notifications_count = 0
    # make a list only with the collectibles that have not already been collected
    # i.e. with owner = 0x0000000000000000000000000000000000000000
    collectibles_free = []
    if not Contract.CONTRACTS_DEPLOYED:
        return render_template("index2.html", user = current_user, collectibles=collectibles_free, balance=balance, notifications_count=notifications_count)
    for collectible in collectibles:
        curr_id = int(collectible.replace(".jpg", ""))
        if Contract.nft_instance.functions.ownerOf(curr_id).call() == "0x0000000000000000000000000000000000000000":
            collectibles_free.append(collectible)
    # get the number of notifications
    # get ten random collectibles from the static folder
    return render_template("index2.html", user = current_user, collectibles=collectibles_free, balance = balance, notifications_count= notifications_count)


@home.route("/mint", methods=["POST"])
@login_required
def mint(): 
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    collectible = request.form.get("collectible")
    id = int(collectible.replace(".jpg", ""))
    if Contract.nft_instance.functions.ownerOf(id).call() == "0x0000000000000000000000000000000000000000":
        if current_user.role == "USER":
            try:
                tx = {
                    "from": current_user.id,
                    "to": Contract.nft_address,
                    "gas": 2000000,
                    "gasPrice": w3.toWei("40", "gwei"),
                }
                tx_hash = Contract.nft_instance.functions.createToken(int(id), collectible).transact(
                    tx
                )
                bid_txn_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                
            except Exception as e:
                flash(f"Error: {e['message']}", "danger")
        if current_user.role == "MANAGER":
            try:
                tx = {
                    "from": owner.address,
                    "to": Contract.lottery_address,
                    "gas": 2000000,
                    "gasPrice": w3.toWei("40", "gwei"),
                }
                # random class number
                classprize = randint(1,10000)%8
                tx_hash = Contract.lottery_instance.functions.buyCollectibles(collectible, classprize, id).transact(
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

# lottery route
@home.route("/lottery", methods=["GET", "POST"])
@login_required
def lottery():
    isLotteryActive = False
    isRoundActive = False
    prizes = False
    if Contract.CONTRACTS_DEPLOYED:
        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()  
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call() 
    error_msg = ""
    # put in session the state of the user
    if request.method == "GET":
        # flash the user role to the template
        if(current_user.role == 'MANAGER'):
            # get the round status from the lottery contract
            return render_template("lottery_manager.html", user = current_user, prizes = prizes, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, error = error_msg, notifications_count = 0)
        if(current_user.role == 'USER'):
            subscribed = session['subscribed']
            if(subscribed == True):
                calculate_notifications()
                notifications_count = len(session.get('events', []))
            else:
                notifications_count = 0
            return render_template("lottery_user.html", user = current_user, isRoundActive=isRoundActive, error = error_msg, subscribed = subscribed, notifications_count = notifications_count)
    
    if request.method == "POST":
        if not Contract.CONTRACTS_DEPLOYED:
            flash("Contracts not deployed yet", "danger")
            return redirect(url_for("home.index"))
        calculate_notifications()
        notifications_count = len(session['events'])
        first_number = int(request.form.get("firstnumber"))
        second_number = int(request.form.get("secondnumber"))
        third_number = int(request.form.get("thirdnumber"))
        fourth_number = int(request.form.get("fourthnumber"))
        fifth_number = int(request.form.get("fifthnumber"))
        powerball_number = int(request.form.get("powerballnumber"))
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

@home.route("/lottery/subscribe", methods=["GET"])
@login_required
def lottery_subscribe():

    session['subscribed'] = True
    session['events'] = []
    session['start_notifications'] = w3.eth.blockNumber

    return redirect(url_for(".lottery"))

@home.route("/lottery/start", methods = ["GET"])
@login_required
def start_lottery():

    if Contract.CONTRACTS_DEPLOYED:
        flash("Contracts already deployed", "danger")
        return redirect(url_for(".lottery")) 
    
    Contract.deploy_lottery()
    print(Contract.CONTRACTS_DEPLOYED)
    error_msg = ""
    isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()
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
   
@home.route("/lottery/round", methods=["GET", "POST"])
@login_required
def lottery_round():
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    error_msg = ""
    if current_user.role == 'MANAGER':
        # active the round in the lottery contract
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

@home.route("/lottery/destroylottery", methods=["GET"])
@login_required
def destroy_lottery():
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    error_msg = ""
    if current_user.role == 'MANAGER':
        # destroy the lottery contract
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
        # return render_template("lottery_manager.html",  user = current_user, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, error = error_msg, notifications_count = 0)

@home.route("/lottery/drawnumbers", methods=["GET"])
@login_required
def draw_numbers():
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    error_msg = ""
    if current_user.role == 'MANAGER':
        # draw the numbers
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
            if status != 1:
                block_number = bid_txn_receipt.get("blockNumber")
                end = Contract.lottery_instance.functions.end().call()
                k = Contract.lottery_instance.functions.K().call()
                if block_number < end:
                    error_msg = "The round is not finished"
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
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call()
        return render_template("lottery_manager.html",  user = current_user, error = error_msg, prizes = prizes, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, notifications_count = 0)

@home.route("/lottery/assignprizes", methods=["GET"])
@login_required
def assign_prizes():
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    error_msg = ""
    if current_user.role == 'MANAGER':
        # assign the prizes
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
        isLotteryActive = Contract.lottery_instance.functions.isLotteryActive().call()
        isRoundActive = Contract.lottery_instance.functions.isRoundActive().call()
        prizes = Contract.lottery_instance.functions.prizesAssigned().call()
        return render_template("lottery_manager.html",  user = current_user, error = error_msg, prizes = prizes, isLotteryActive = isLotteryActive, isRoundActive=isRoundActive, notifications_count = 0)

def calculate_notifications():
    if not Contract.CONTRACTS_DEPLOYED:
        return
    
    events_entries = (
            Contract.lottery_start_event.get_all_entries()
            + Contract.lottery_close_event.get_all_entries()
            + Contract.draw_numbers_event.get_all_entries()
            + Contract.prizes_assigned_event.get_all_entries()
            + Contract.round_start_event.get_all_entries()
        )
    
    # Order by block number the first block is the latest
    events_entries.sort(key=lambda x: x.blockNumber, reverse=True)

    for e in events_entries:
        block_id = e.blockNumber
        event = e.event
        args = e.args
        if block_id <= session['start_notifications'] or event == "mintToken":
            continue
        block_id = str(e.blockNumber)
        # Check if the event is already notified
        if not session.get(block_id):
            session[block_id] = []
      
        if event == "assignPrize":
            if (event, args.get('id')) not in session.get(block_id):
                session[block_id].append((event,args.get('id')))
                session['events'].append("Prize Assigned")
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
               
@home.route("/notifications", methods=["GET"])
@login_required
def notifications():
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    if request.method == "GET":
        if session['subscribed'] == True:
            calculate_notifications()
            return render_template("notifications.html", user = current_user, events=(session['events'][::-1]), subscribed = session['subscribed'], notifications_count = len(session['events']))
        else:
            return render_template("notifications.html", events = [], user = current_user, subscribed = session['subscribed'], notifications_count = 0)

@home.route("/notifications/deleteall", methods=["GET"])  
@login_required
def delete_all_notifications():
    if not Contract.CONTRACTS_DEPLOYED:
        flash("Contracts not deployed yet", "danger")
        return redirect(url_for("home.index"))
    
    if request.method == "GET":
        session['events'] = []
        notifications_count = 0
        return render_template("notifications.html", events = [], user = current_user, subscribed = session['subscribed'], notifications_count = notifications_count)