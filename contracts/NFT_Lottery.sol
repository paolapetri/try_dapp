// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;


// Smart contract code implementing the NFT 
// import "@openzeppelin/contracts/utils/Strings.sol";
// import "hardhat/console.sol";
import "./NFT_ERC721.sol";

contract NFT_Lottery {

    // EVENTS
    event lotteryStart();
    event closeLottery();

    event roundStart(uint256 startingBlock, uint256 endingBlock);
    event roundEnd();

    event mintToken(address to, uint256 tokenId, string description);

    event boughtTicket(address user, uint256 firstNumber, uint256 secondNumber, uint256 thirdNumber, uint256 fourthNumber, uint256 fifthNumber, uint256 powerballNumber);

    event drawing(uint256 firstNumber, uint256 secondNumber, uint256 thirdNumber, uint256 fourthNumber, uint256 fifthNumber, uint256 powerballNumber);

    event assignPrize(address winner, uint256 id);

    // lottery manager address
    address public lotteryManager;

    // Collectibles
    struct Collectible {
        uint256 id;
        string image;
        bool salable;
    }

    // mapping of collectible to their class
    // the class represents the collectible's prize "difficulty", i.e. how many matching numbers in the ticket
    mapping (uint256 => Collectible[]) public collectibleClasses;
    
    // counter for the collectible unique id
    uint256 public collectibleIdCounter = 201;

    // instance of the NFT contract
    NFT_ERC721 public nft;

    // Mapping between the matches and the class
    mapping (uint256 => uint256) public matchesClasses;
    bool public roundActive;

    /// @notice msg.sender is the owner of the contract
    /// @param _nftAddress address of the nft contract
    /// @param duration The duration of the round in block numbers.
    constructor(address _nftAddress, uint256 duration) payable {
        lotteryManager = msg.sender;
        nft = NFT_ERC721(_nftAddress);
        M = duration;
        isLotteryActive = false;
        prizesAssigned = true;

        // initialize mapping between classes and matches
        uint class = 7;
        for (uint i = 1; i < 6; i++) {
            matchesClasses[i] = class;
            class --;
        }
        end = 0;
        // Open the furst new round
       // end = block.number + M;
    }


    // boolean to keep the state of the lottery smart contract
    // used because the lottery operator can close the lottery
    bool public isLotteryActive;
    // Lottery tickets (owner, 5 numbers, 1 special Powerball number)
    struct Ticket {
        address owner;
        uint256 firstNumber;
        uint256 secondNumber;
        uint256 thirdNumber;
        uint256 fourthNumber;
        uint256 fifthNumber;
        uint256 powerballNumber;
    }

    // Ticket price
    uint256 public constant TICKET_PRICE = 10 gwei;

    // Active tickets from the current round 
    Ticket[] public roundTickets;

    // Number useful for RNG
    // uint256 public D = 283; 

    // Round duration expressed in blocks number
    uint256 public M;

    // Number of blocks that the manager has to wait before drawing numbers because of the RNG
    // Assume that this number has a fixed value
    uint256 public K = 3;

    // Number of the ending block of the current round 
    // Will be generated adding M to the starting (current) block number
    uint256 public end;
    
    // Bool to keep the state of the current round, set to true only if the previous round is finished, the numbers have been
    // drawn and the prizes have been assigned
    bool public prizesAssigned;

    // Winning ticket of the current round
    Ticket public winner;

    // Random number generator that uses the (endBlock+K)th block hash to draw numbers
    function randomDrawing(uint256 i) public view returns (uint256) {
        require(block.number >= end + K, "The numbers cannot be drawn");
        uint256 number = uint256(keccak256(abi.encode(blockhash(end + K), K, end, i)));
        return number;
    }


    // Random number generator that uses a source of randomness provided by the blockchain
    // useful only for random number generator purposes (i.e. class assignment, prize assignment)
    // and not for number drawing
    function randomNumberGenerator(uint256 D) public view returns (uint256) {
        // uint256 seed = uint256(keccak256(abi.encodePacked(block.timestamp + block.difficulty + ((uint256(keccak256(abi.encodePacked(block.coinbase)))) / (block.timestamp)) + block.gaslimit + ((uint256(keccak256(abi.encodePacked(msg.sender)))) / (block.timestamp)) + block.number)));
        // return (seed - ((seed / D) * D));
         return uint(keccak256(abi.encodePacked(block.difficulty, block.timestamp, D)));
    }

    /// @notice The lottery operator mint new token
    /// @dev Throws unless `msg.sender` is the lottery manager
    /// @dev Throws unless the lottery is active
    /// @param nftImage The string containing a description of the collectible
    /// @param classNum The class of the collectible (useful if the class list is empty and 
    /// the lottery manager has to generate the collectible of a particular class to give it as a prize
    function buyCollectibles(string memory nftImage, uint256 classNum, uint256 id) public {
        require(msg.sender == lotteryManager, "Only the lottery manager can buy collectibles");
        require(isLotteryActive, "Lottery smart contract is not active");
        require(classNum >=1 && classNum <= 8, "Class number is not valid");
      
        // id of the collectible is a counter incremented by 1 each time a collectible is minted to give it a unique id
        // add collectible to the class mapping
        collectibleClasses[classNum].push(Collectible(id, nftImage, true));

        // mint the collectible
        nft.createToken(id, nftImage);
        emit mintToken(msg.sender, id, nftImage);
    }

    function createLottery() public {
        require(!isLotteryActive, "Lottery smart contract is already active");
        isLotteryActive = true;
        emit lotteryStart();
    }

    /// @notice The lottery operator can close the contract and stop the lottery, even if a round is active
    /// the partecipants that have already bought a ticket will be refunded
    /// @dev Throws unless `msg.sender` is the current owner
    /// @dev Throws unless the lottery is active
    function destroyLottery() public {
        require(msg.sender == lotteryManager, "Only the lottery manager can close the lottery");
        require(isLotteryActive, "Lottery is not active");
        // Lottery smart contract is closed
        isLotteryActive = false;
        prizesAssigned = true;
        winner.firstNumber = 0;
        winner.secondNumber = 0;
        winner.thirdNumber = 0;
        winner.fourthNumber = 0;
        winner.fifthNumber = 0;
        winner.powerballNumber = 0;
        // If the round is active, refund the partecipants that have already bought a ticket with a sum equal to the ticket price
        if (isRoundActive()) {
            for (uint256 i = 0; i < roundTickets.length; i++) {
                payable(roundTickets[i].owner).transfer(TICKET_PRICE);
            }
        }
        roundActive = false;

        emit closeLottery();
    }

    /// @notice Check if the round is active.
    function isRoundActive() public view returns (bool) {
        // The round is active if current block number is M numbers greater than the starting block number 
        // the end number has been defined at the opening of the round
        return (end >= block.number && roundActive);
    }
    

    /// @notice The lottery operator can open a new round.
    /// The lottery operator can only open a new round if the previous round is finished.
    /// @dev Throws unless `msg.sender` is the current owner or the lottery is not finished
    /// @dev Throws unless the lottery is active
    /// @dev Throws if the round is yet open
    /// @dev Throws if the round is not finished (prize not assigned)
    /// @dev Throws if the numbers of the previous round have not been drawn (the winner ticket has not been updated)
    function newRound() public {
        require(isLotteryActive, "Lottery is not active");
        require(msg.sender == lotteryManager, "Only the lottery manager can open a new round");
        require(!isRoundActive(), "The round is already open");
        require(prizesAssigned, "The previous round is not finished");
        require(winner.powerballNumber == 0, "The numbers of the previous round have not been drawn");
        
        // Clean the data of the previous round
        delete roundTickets;

        // start a new round
        prizesAssigned = false;
        // define the ending block number of the round
        end = block.number + M;    
        roundActive = true;
        emit roundStart(block.number, end);
    }

    /// @notice The user buys a ticket and choose 5 numbers and 1 special powerball number
    /// @dev Throws unless the lottery is active
    /// @dev Throws unless `msg.sender` has sent enough gwei to buy the ticket
    /// @dev Throws unless `firstNumber`, `secondNumber`, `thirdNumber`, `fourthNumber`, `fifthNumber`, `powerballNumber` are valid numbers
    /// @param firstNumber The first number of the ticket
    /// @param secondNumber The second number of the ticket
    /// @param thirdNumber The third number of the ticket
    /// @param fourthNumber The fourth number of the ticket
    /// @param fifthNumber The fifth number of the ticket
    /// @param powerballNumber The special powerball number of the ticket
    function buyTicket(uint256 firstNumber, uint256 secondNumber, uint256 thirdNumber, uint256 fourthNumber, uint256 fifthNumber, uint256 powerballNumber) public payable {
        require(isLotteryActive, "Lottery is not active");
        require(isRoundActive(), "Round is not active");
        require(msg.value == TICKET_PRICE, "The price for a ticket is 10 gwei");
        require (firstNumber >= 1 && firstNumber <= 69, "The first number must be between 1 and 69");
        require (secondNumber >= 1 && secondNumber <= 69, "The second number must be between 1 and 69");
        require (thirdNumber >= 1 && thirdNumber <= 69, "The third number must be between 1 and 69");
        require (fourthNumber >= 1 && fourthNumber <= 69, "The fourth number must be between 1 and 69");
        require (fifthNumber >= 1 && fifthNumber <= 69, "The fifth number must be between 1 and 69");
        require(powerballNumber >= 1 && powerballNumber <= 26, "The powerball number must be between 1 and 26");
        require(firstNumber != secondNumber && firstNumber != thirdNumber && firstNumber != fourthNumber && firstNumber != fifthNumber && secondNumber != thirdNumber && secondNumber != fourthNumber && secondNumber != fifthNumber && thirdNumber != fourthNumber && thirdNumber != fifthNumber, "The numbers must be different");
        require(firstNumber != powerballNumber && secondNumber != powerballNumber && thirdNumber != powerballNumber && fourthNumber != powerballNumber && fifthNumber != powerballNumber, "The powerball number must be different");
        // insert a ticket in the array of tickets bought in the current round
        roundTickets.push(Ticket(msg.sender, firstNumber, secondNumber, thirdNumber, fourthNumber, fifthNumber, powerballNumber));

        emit boughtTicket(msg.sender, firstNumber, secondNumber, thirdNumber, fourthNumber, fifthNumber, powerballNumber);
    }

    /// @notice Draw winning numbers of the current lottery round
    /// @dev Throws unless `msg.sender` is the lottery operator
    /// @dev Throws unless the lottery is active
    /// @dev Throws unless the previous round is not active (users can still buy tickets)
    /// @dev Throws unless the previous round is not finished (prize not assigned)
    /// @dev Throws if the numbers of the previous round have already been drawn (winner numbers has been updated)
    function drawNumbers() public {
        require(msg.sender == lotteryManager, "Only the lottery manager can draw numbers");
        require(isLotteryActive, "Lottery is not active");
        require(!isRoundActive(), "Round is not yet finished");
        require(!prizesAssigned, "Round is already finished");
        require(winner.powerballNumber == 0, "The numbers of the previous round have already been drawn");

        // extract six random numbers in the correct ranges
        uint256 firstNumber = uint256((randomDrawing(1) % 69) + 1);
        uint256 secondNumber = uint256((randomDrawing(2) % 69) + 1);
        uint256 thirdNumber = uint256((randomDrawing(3) % 69) + 1);
        uint256 fourthNumber = uint256((randomDrawing(4) % 69) + 1);
        uint256 fifthNumber = uint256((randomDrawing(5) % 69) + 1);
        uint256 powerballNumber = uint256((randomDrawing(6) % 26) + 1);

        // save the winning numbers without owner (because it is not needed to save the winning numbers)
        winner = Ticket(address(0), firstNumber, secondNumber, thirdNumber, fourthNumber, fifthNumber, powerballNumber);

        emit drawing(firstNumber, secondNumber, thirdNumber, fourthNumber, fifthNumber, powerballNumber);
    }

    /// @notice Get the class prize of the current lottery round based on the number of matching numbers
    /// @param matches The number of matching numbers
    /// @param powerballMatch True if the powerball matches the winning ticket powerball, false otherwise
    /// @dev Throws unless the lottery is active
    /// @return number of class 
    function getClassPrize(uint8 matches, bool powerballMatch) internal view returns (uint256){
        require(isLotteryActive, "Lottery is not active");
        uint256 class;
        if(!powerballMatch) {
            class = matchesClasses[matches];
        }
        else {
            if (matches == 5) {
                class = 1;
            }
            else if (matches == 4) {
                class = 3;
            }
            else if (matches == 3) {
                class = 4;
            }
            else if (matches == 2) {
                class = 5;
            }
            else if (matches == 1) {
                class = 6;
            }
            else if (matches == 0) {
                class = 8;
            }

        }
        return class;
    }

    function toString(uint256 value) internal pure returns (string memory) {
        // Inspired by OraclizeAPI's implementation - MIT licence
        // https://github.com/oraclize/ethereum-api/blob/b42146b063c7d6ee1358846c198246239e9360e8/oraclizeAPI_0.4.25.sol

        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }

    /// @notice Distribute the prizes of the current lottery round
    /// @dev Throws unless `msg.sender` is the lottery operator
    /// @dev Throws unless the lottery is active
    /// @dev Throws unless `winningTicket` is already drawn
    /// @dev Throws unless `winner` is not defined
    function givePrizes() public {
        require(msg.sender == lotteryManager, "Only the lottery manager can distribute prizes");
        require(isLotteryActive, "Lottery is not active");
        require(winner.powerballNumber != 0, "Won numbers are not drawn");
        require(!isRoundActive(), "Round is not yet finished");
        if (roundTickets.length != 0){

        // for each played ticket check the number of matching numbers and the powerball number
        for (uint256 i = 0; i < roundTickets.length; i++) {
            Ticket memory currTicket = roundTickets[i];

            // number of matching number
            uint8 matches;
            //bool for powerball matching
            bool powerballMatch = false;

            // current ticket 
            // create an array with the played numbers
            uint256[5] memory playedNumbers = [currTicket.firstNumber, currTicket.secondNumber, currTicket.thirdNumber, currTicket.fourthNumber, currTicket.fifthNumber];
            
            // create an array with the winning numbers
            uint256[5] memory winningNumbers = [winner.firstNumber, winner.secondNumber, winner.thirdNumber, winner.fourthNumber, winner.fifthNumber];
            // for each played number check if it matches one of the drawn number 
            for (uint j = 0; j < 5; j++) {
                uint256 currNumber = playedNumbers[j];
                for (uint k = 0; k < 5; k++){
                    // count the matches (if there are some)
                    if (currNumber == winningNumbers[k]) {
                        matches++;
                    }
                }
            }

            // check if the powerball matches the winning ticket powerball
            if (currTicket.powerballNumber == winner.powerballNumber) {
                powerballMatch = true;
            }
    
            // if there are matches (also only the powerball), get the class prize and distribute the prize
            // compute the class prize of the current ticket depending on the number of matches and the powerball match
            if(matches > 0 || powerballMatch) {
                uint256 classNum = getClassPrize(matches, powerballMatch);
                bool done = false;
                if (collectibleClasses[classNum].length  != 0) {
                    for (uint256 z; z < collectibleClasses[classNum].length; z++) {
                        if (collectibleClasses[classNum][z].salable == true) {
                            done = true;
                            nft.transferFrom(address(this), roundTickets[i].owner, collectibleClasses[classNum][z].id);
                            collectibleClasses[classNum][z].salable = false;
                            emit assignPrize(roundTickets[i].owner, collectibleClasses[classNum][z].id );

                            break;
                        }
                    }
                }
                if (collectibleClasses[classNum].length == 0 || done == false){
                    // if there are no collectible classes of this class, mint a collectible whose owner is address(0)
                    // check the owner
                    for (uint256 t = 1; t < 200; t++) {
                        if(nft.ownerOf(t) == address(0)) {
                           nft.createToken(t, string(abi.encodePacked(toString(t),".jpg")));
                           nft.transferFrom(address(this), roundTickets[i].owner, t);
                           emit assignPrize(roundTickets[i].owner, t);

                           break;
                        }
                    }
                }
                
                }
            }
        }
            
        
        prizesAssigned = true;
        delete winner;
        emit roundEnd();
        //at the end of each round the lottery manager takes the money of the tickets sold 
        // send 10 gwei to lottery manager address for each ticket sold
        payable(lotteryManager).transfer(roundTickets.length * TICKET_PRICE);


    }
  
}