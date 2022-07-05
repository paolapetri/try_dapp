// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

abstract contract ERC721 {
  function balanceOf(address _owner) external virtual view returns (uint256) ;
  function ownerOf(uint256 _tokenId) external virtual view returns (address);
  function transferFrom(address _from, address _to, uint256 _tokenId) external virtual payable;
  function approve(address _approved, uint256 _tokenId) external virtual payable;
  function getApproved(uint256 _tokenId) external virtual view returns (address);
  function setApprovalForAll(address _operator, bool _approved) external virtual;
  function isApprovedForAll(address _owner, address _operator) external view virtual returns (bool);
   

  /// @dev This emits when an operator is enabled or disabled for an owner.
  ///  The operator can manage all NFTs of the owner
  event ApprovalForAll(address indexed _owner, address indexed _operator, bool _approved);

  /// @dev This emits when ownership of any NFT changes by any mechanism.
  /// This event emits when NFTs are created (`from` == 0) and destroyed
  /// (`to` == 0). Exception: during contract creation, any number of NFTs
  /// may be created and assigned without emitting Transfer. At the time of
  /// any transfer, the approved address for that NFT (if any) is reset to none.
  event Transfer(address indexed _from, address indexed _to, uint256 indexed _tokenId);

  /// @dev This emits when the approved address for an NFT is changed or
  ///  reaffirmed. The zero address indicates there is no approved address.
  ///  When a Transfer event emits, this also indicates that the approved
  ///  address for that NFT (if any) is reset to none.
  event Approval(address indexed _owner, address indexed _approved, uint256 indexed _tokenId);
}
