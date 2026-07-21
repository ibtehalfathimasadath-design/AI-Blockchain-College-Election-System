// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * ElectionVoting Smart Contract
 * College Election System — Ethereum-based vote storage
 *
 * Stores: votes, nominations-approved status, and voter registry
 * Events: VoteCast, NominationApproved, ElectionReset
 * All writes produce real on-chain transactions with tx hash.
 */
contract ElectionVoting {

    // ─────────────────────────────────────────
    //  State Variables
    // ─────────────────────────────────────────

    address public admin;

    struct Vote {
        uint256 voterId;
        string  voterName;
        string  role;
        uint256 nominationId;
        uint256 timestamp;
        bool    exists;
    }

    struct Nomination {
        uint256 id;
        string  name;
        string  department;
        string  role;
        bool    approved;
        bool    exists;
    }

    // voterId  → role → Vote
    mapping(uint256 => mapping(string => Vote)) public votes;

    // voterId → has voted at all
    mapping(uint256 => bool) public hasVoted;

    // nominationId → Nomination
    mapping(uint256 => Nomination) public nominations;

    // role → list of nomination ids
    mapping(string => uint256[]) private nominationsByRole;

    // All voter IDs that have voted (for iteration)
    uint256[] public voterIds;

    uint256 public totalVotes;
    uint256 public totalNominations;

    bool public electionActive;

    // ─────────────────────────────────────────
    //  Events  (emitted on every state change)
    // ─────────────────────────────────────────

    event VoteCast(
        uint256 indexed voterId,
        string  voterName,
        uint256 indexed nominationId,
        string  role,
        uint256 timestamp
    );

    event NominationRegistered(
        uint256 indexed nominationId,
        string  name,
        string  role,
        bool    approved
    );

    event NominationStatusUpdated(
        uint256 indexed nominationId,
        bool    approved
    );

    event ElectionReset(address indexed by, uint256 timestamp);

    event ElectionStatusChanged(bool active, address indexed by);

    // ─────────────────────────────────────────
    //  Modifiers
    // ─────────────────────────────────────────

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this");
        _;
    }

    modifier whenElectionActive() {
        require(electionActive, "Election is not active");
        _;
    }

    // ─────────────────────────────────────────
    //  Constructor
    // ─────────────────────────────────────────

    constructor() {
        admin = msg.sender;
        electionActive = true;
    }

    // ─────────────────────────────────────────
    //  Write Functions (generate transactions)
    // ─────────────────────────────────────────

    /**
     * @notice Register a nomination on-chain (called when admin approves)
     */
    function registerNomination(
        uint256 nominationId,
        string calldata name,
        string calldata department,
        string calldata role,
        bool approved
    ) external onlyAdmin {
        require(!nominations[nominationId].exists, "Nomination already registered");

        nominations[nominationId] = Nomination({
            id:         nominationId,
            name:       name,
            department: department,
            role:       role,
            approved:   approved,
            exists:     true
        });

        nominationsByRole[role].push(nominationId);
        totalNominations++;

        emit NominationRegistered(nominationId, name, role, approved);
    }

    /**
     * @notice Update nomination approval status
     */
    function updateNominationStatus(
        uint256 nominationId,
        bool approved
    ) external onlyAdmin {
        require(nominations[nominationId].exists, "Nomination not found");
        nominations[nominationId].approved = approved;
        emit NominationStatusUpdated(nominationId, approved);
    }

    /**
     * @notice Cast a vote — one vote per voter per role
     * @param voterId      Numeric user ID from Flask DB
     * @param voterName    Display name
     * @param nominationId The chosen nomination ID
     * @param role         Election role (President, Secretary, etc.)
     */
    function castVote(
        uint256 voterId,
        string calldata voterName,
        uint256 nominationId,
        string calldata role
    ) external whenElectionActive {
        // Prevent double-voting for the same role
        require(!votes[voterId][role].exists, "Already voted for this role");

        // Nomination must be approved
        require(nominations[nominationId].exists, "Nomination not registered");
        require(nominations[nominationId].approved, "Nomination not approved");

        uint256 ts = block.timestamp;

        votes[voterId][role] = Vote({
            voterId:      voterId,
            voterName:    voterName,
            role:         role,
            nominationId: nominationId,
            timestamp:    ts,
            exists:       true
        });

        if (!hasVoted[voterId]) {
            hasVoted[voterId] = true;
            voterIds.push(voterId);
        }

        totalVotes++;

        emit VoteCast(voterId, voterName, nominationId, role, ts);
    }

    // ─────────────────────────────────────────
    //  Admin Controls
    // ─────────────────────────────────────────

    function setElectionActive(bool active) external onlyAdmin {
        electionActive = active;
        emit ElectionStatusChanged(active, msg.sender);
    }

    function resetElection() external onlyAdmin {
        // Clear voter tracking (note: mappings can't be fully deleted in Solidity,
        // but we reset the voterIds array so old entries are ignored)
        for (uint256 i = 0; i < voterIds.length; i++) {
            hasVoted[voterIds[i]] = false;
        }
        delete voterIds;
        totalVotes = 0;
        emit ElectionReset(msg.sender, block.timestamp);
    }

    // ─────────────────────────────────────────
    //  View / Read Functions (free — no gas)
    // ─────────────────────────────────────────

    function getVote(uint256 voterId, string calldata role)
        external view
        returns (uint256 nominationId, string memory voterName, uint256 timestamp, bool exists)
    {
        Vote memory v = votes[voterId][role];
        return (v.nominationId, v.voterName, v.timestamp, v.exists);
    }

    function getNomination(uint256 nominationId)
        external view
        returns (string memory name, string memory department, string memory role, bool approved, bool exists)
    {
        Nomination memory n = nominations[nominationId];
        return (n.name, n.department, n.role, n.approved, n.exists);
    }

    function getTotalVotes() external view returns (uint256) {
        return totalVotes;
    }

    function getVoterCount() external view returns (uint256) {
        return voterIds.length;
    }

    function getNominationsByRole(string calldata role)
        external view
        returns (uint256[] memory)
    {
        return nominationsByRole[role];
    }

    function isAdmin(address addr) external view returns (bool) {
        return addr == admin;
    }
}
