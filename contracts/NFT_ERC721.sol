// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

// Smart contract code implementing ERC721 token standard

import "./ERC721.sol";

contract NFT_ERC721 is ERC721 {

    // Mapping owner address to token count
    mapping(address => uint256) _balances;

    // Mapping token id to owner address
    mapping(uint256 => address) _owners;

    // Mapping token id to image description
    mapping(uint256 => string) images;

    // Mapping from token ID to approved address
    mapping(uint256 => address) _tokenApprovals;

    // Mapping from owner address to operator approvals
    mapping(address => mapping(address => bool)) _operatorApprovals;

    /// @notice Count all NFTs assigned to an owner
    /// @dev NFTs assigned to the zero address are considered invalid, and this
    ///  function throws for queries about the zero address.
    /// @param _owner An address for whom to query the balance
    /// @return The number of NFTs owned by `_owner`, possibly zero
    function balanceOf(address _owner) public view override returns (uint256) {
        return _balances[_owner];
    }

    /// @notice Find the owner of an NFT
    /// @dev NFTs assigned to zero address are considered invalid, and queries
    ///  about them do throw.
    /// @param _tokenId The identifier for an NFT
    /// @return The address of the owner of the NFT
    function ownerOf(uint256 _tokenId) public view override returns (address) {
        return _owners[_tokenId];
    }

   
    /// @notice Transfer ownership of an NFT -- THE CALLER IS RESPONSIBLE
    ///  TO CONFIRM THAT `_to` IS CAPABLE OF RECEIVING NFTS OR ELSE
    ///  THEY MAY BE PERMANENTLY LOST
    /// @dev Throws unless `msg.sender` is the current owner, an authorized
    ///  operator, or the approved address for this NFT. Throws if `_from` is
    ///  not the current owner. Throws if `_to` is the zero address. Throws if
    ///  `_tokenId` is not a valid NFT.
    /// @param _from The current owner of the NFT
    /// @param _to The new owner
    /// @param _tokenId The NFT to transfer
    function transferFrom(address _from, address _to, uint256 _tokenId) external payable override{
        // the from address must be the messsage sender and should possess the token or an approved address or an operator
        require((_from == msg.sender && _owners[_tokenId] == _from) || _from == _tokenApprovals[_tokenId] || _operatorApprovals[_owners[_tokenId]][msg.sender], "Sender is not the owner or approved address or operator");

        
        // update the balance of both the old and the new owner
        _balances[_owners[_tokenId]]--;
        
        // change the token owner
        _owners[_tokenId] = _to;

        _balances[_to]++;
        emit Transfer(_from, _to, _tokenId);
    }
    /// @notice Set or reaffirm the approved address for an NFT
    /// @dev The zero address indicates there is no approved address.
    /// @dev Throws unless `msg.sender` is the current NFT owner, or an authorized
    ///  operator of the current owner.
    /// @param _approved The new approved NFT controller
    /// @param _tokenId The NFT to approve
    function approve(address _approved, uint256 _tokenId) external payable override{
        // the approve must be called by the owner of the token or by operator
        require(msg.sender == _owners[_tokenId] || _operatorApprovals[_owners[_tokenId]][msg.sender],
            "Only the owner or operator can approve"
        );

        // set or reaffirm the approved address
        _tokenApprovals[_tokenId] = _approved;
        emit Approval(msg.sender, _approved, _tokenId);
    }

    /// @notice Enable or disable approval for a third party ("operator") to manage
    ///  all of `msg.sender`'s assets.
    /// @dev Emits the ApprovalForAll event. The contract MUST allow
    ///  multiple operators per owner.
    /// @param _operator Address to add to the set of authorized operators.
    /// @param _approved True if the operator is approved, false to revoke approval
    function setApprovalForAll(address _operator, bool _approved) external override{
        _operatorApprovals[msg.sender][_operator] = _approved;
        emit ApprovalForAll(msg.sender, _operator, _approved);

    }

    /// @notice Get the approved address for a single NFT
    /// @dev Throws if `_tokenId` is not a valid NFT
    /// @param _tokenId The NFT to find the approved address for
    /// @return The approved address for this NFT, or the zero address if there is none
    function getApproved(uint256 _tokenId) public view override returns (address) {
       return _tokenApprovals[_tokenId];
    }

    /// @notice Query if an address is an authorized operator for another address
    /// @param _owner The address that owns the NFTs
    /// @param _operator The address that acts on behalf of the owner
    /// @return True if `_operator` is an approved operator for `_owner`, false otherwise
    function isApprovedForAll(address _owner, address _operator) external view virtual override returns (bool) {
        return _operatorApprovals[_owner][_operator];
    }

    function createToken(uint256 _tokenId, string memory _collectible) public {
        // the token must not exist
        require(_owners[_tokenId] == address(0));
        // create the token with msg.sender as owner
        _owners[_tokenId] = msg.sender;
        images[_tokenId] = _collectible;
        //update the balance of the msg.sender
        _balances[msg.sender]++;
    }


}