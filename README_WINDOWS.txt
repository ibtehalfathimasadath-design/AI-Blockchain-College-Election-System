====================================================================
  COLLEGE ELECTION SYSTEM — WINDOWS BLOCKCHAIN SETUP
  Step-by-Step Guide (Ganache, 15 Minutes)
====================================================================

FOLDER STRUCTURE AFTER EXTRACTION:
-----------------------------------
blockchain_upgrade\
  ├── 1_setup.bat              ← RUN THIS FIRST
  ├── 2_deploy_contract.bat    ← RUN THIS SECOND
  ├── 3_start_app.bat          ← RUN THIS THIRD
  ├── 4_check_blockchain.bat   ← RUN THIS TO VERIFY
  ├── contracts\
  ├── scripts\
  ├── utils\
  ├── templates\
  ├── static\
  └── README_WINDOWS.txt       ← THIS FILE


====================================================================
PRE-REQUISITES (Install Before Starting)
====================================================================

  1. NODE.JS  (required for smart contract)
     Download: https://nodejs.org
     Click "LTS" version → Install with all defaults
     Verify in CMD:  node --version   (should show v18 or v20)

  2. PYTHON  (already installed for Flask app)
     Verify in CMD:  python --version

  3. GANACHE GUI  (local Ethereum blockchain)
     Download: https://trufflesuite.com/ganache
     Install and launch it (keep it running throughout)


====================================================================
STEP 1 — RUN SETUP (3 minutes)
====================================================================

  IMPORTANT: Place the blockchain_upgrade folder NEXT TO your
  election_ocr_fixed folder, like this:

      C:\YourProjects\
          ├── election_ocr_fixed\   ← your Flask app
          └── blockchain_upgrade\   ← this folder

  Then:

  1. Open CMD in the blockchain_upgrade folder:
     - Hold SHIFT + Right-click inside the blockchain_upgrade folder
     - Click "Open PowerShell window here" or "Open CMD window here"

  2. Type:
         1_setup.bat
     and press Enter

  3. The script will:
     ✓ Check Node.js and Python are installed
     ✓ Install web3 and python-dotenv Python packages
     ✓ Copy Hardhat files and set up the project
     ✓ Run npm install (downloads Hardhat — takes 1-2 min)
     ✓ Compile ElectionVoting.sol
     ✓ Copy updated Flask files into election_ocr_fixed
     ✓ Open .env in Notepad automatically


====================================================================
STEP 2 — CONFIGURE GANACHE (3 minutes)
====================================================================

  After 1_setup.bat finishes, Notepad opens .env. Do this:

  A. OPEN GANACHE GUI
     - Launch Ganache (from Start Menu or Desktop)
     - Click "New Workspace"
     - Click "Ethereum"
     - Click "Save"
     - You see 10 accounts each with 100 ETH

  B. FIND THE RPC URL
     - Look at the top of Ganache window
     - Find the line: "RPC SERVER  http://127.0.0.1:7545"
     - This is your GANACHE_RPC_URL

  C. GET A PRIVATE KEY
     - Click the KEY icon (🔑) next to Account 0 (first account)
     - A popup shows the PRIVATE KEY (long string starting with 0x)
     - Click COPY or select all and Ctrl+C

  D. EDIT .env IN NOTEPAD
     Find these 4 lines and update them:

         BLOCKCHAIN_NETWORK=ganache
         GANACHE_RPC_URL=http://127.0.0.1:7545
         GANACHE_PRIVATE_KEY=0xPASTEYOURKEYHERE
         ELECTION_CONTRACT_ADDRESS=       ← leave blank for now

     Save the file (Ctrl+S) and close Notepad.


====================================================================
STEP 3 — DEPLOY SMART CONTRACT (2 minutes)
====================================================================

  In the same CMD window, type:
      2_deploy_contract.bat
  and press Enter.

  WHAT YOU WILL SEE:
  ------------------
  Deploying with account: 0xABCD1234...
  Account balance: 100000000000000000000

  Compiled 1 Solidity file successfully

  ✅ ElectionVoting deployed to: 0x5FbDB2315678...
  Network: ganache
  Deployment info saved to: ./deployment.json
  ABI saved to: ./ElectionVoting_ABI.json

  ELECTION_CONTRACT_ADDRESS=0x5FbDB2315678...   ← COPY THIS

  ------------------

  The script opens Notepad automatically.
  PASTE the address (0x5FbDB...) next to:
      ELECTION_CONTRACT_ADDRESS=0x5FbDB2315678...

  Save the file (Ctrl+S).

  IN GANACHE GUI — Click "Transactions" tab.
  You should see 1 transaction: the contract deployment!


====================================================================
STEP 4 — APPLY app.py CHANGES (5 minutes)
====================================================================

  Open election_ocr_fixed\app.py in any text editor (Notepad, VS Code).
  Make these 7 changes using the code in app_changes.py as reference:

  CHANGE 1 — Update imports (top of app.py)
  ------------------------------------------
  FIND:
      from utils.blockchain import Blockchain, get_blockchain

  REPLACE WITH:
      from utils.blockchain import Blockchain, get_blockchain, BlockchainClient

  ------------------------------------------
  CHANGE 2 — Replace cast_vote route
  Find the function starting with:
      @app.route('/voter/cast-vote', methods=['GET', 'POST'])
  Replace the ENTIRE function with the code in CAST_VOTE_ROUTE
  inside app_changes.py

  ------------------------------------------
  CHANGE 3 — Replace vote_confirmation route
  Find:
      @app.route('/voter/confirmation/<...>')
  Replace with VOTE_CONFIRMATION_ROUTE from app_changes.py

  ------------------------------------------
  CHANGE 4 — Replace blockchain status API
  Find:
      @app.route('/api/blockchain-status')
  Replace with BLOCKCHAIN_STATUS_API from app_changes.py
  Also add the new /api/blockchain-events route below it.

  ------------------------------------------
  CHANGE 5 — Replace admin_votes route
  Find:
      @app.route('/admin/votes')
  Replace with ADMIN_VOTES_ROUTE from app_changes.py

  ------------------------------------------
  CHANGE 6 — Add blockchain write in nomination approval
  In the update_nomination_status route, after db.commit(),
  add the NOMINATION_STATUS_BLOCKCHAIN_SNIPPET from app_changes.py

  ------------------------------------------
  CHANGE 7 — Pass contract address to cast_vote template
  In the cast_vote GET return, add contract_address:

      return render_template(
          'cast_vote.html',
          candidates_by_role=candidates_by_role,
          contract_address=os.getenv('ELECTION_CONTRACT_ADDRESS', ''),
      )

  Save app.py when done.


====================================================================
STEP 5 — START THE APP (1 minute)
====================================================================

  In CMD, type:
      3_start_app.bat
  and press Enter.

  You should see:
      * Running on http://127.0.0.1:5000
      [Blockchain] ✅ Connected to ganache @ http://127.0.0.1:7545
      [Blockchain]    Chain ID: 1337
      [Blockchain]    Signer: 0xYourAccountAddress
      [Blockchain]    Contract: 0xYourContractAddress

  Open browser: http://localhost:5000


====================================================================
STEP 6 — VERIFY BLOCKCHAIN IS RUNNING
====================================================================

  TEST 1 — Health check script
  In CMD:
      4_check_blockchain.bat

  All items should show OK.

  TEST 2 — API check in browser
  Open: http://localhost:5000/api/blockchain-status

  You should see JSON like:
      {
        "connected": true,
        "network": "ganache",
        "chain_id": 1337,
        "block_number": 1,
        "total_votes": 0,
        "simulated": false
      }

  TEST 3 — Cast a vote and watch Ganache
  1. Log in as a student voter
  2. Verify identity (OCR step)
  3. Go to Cast Vote page
  4. Select candidates and submit
  5. IMMEDIATELY open Ganache GUI → "Transactions" tab
     → You see a NEW transaction with:
        • From: your account address
        • To:   contract address
        • Gas:  ~21,000-50,000 wei
        • Method: castVote

  6. The confirmation page shows:
        Transaction Hash: 0xAbCd1234...  ← REAL Ethereum tx hash
        Block Number: #2
        Gas Used: 45000 wei
        Status: ✅ Confirmed On-Chain

  TEST 4 — Admin blockchain explorer
  Log in as admin → Admin → Votes → "On-Chain Events" tab
  See all VoteCast events fetched directly from the smart contract.


====================================================================
WHAT YOU SEE IN GANACHE GUI
====================================================================

  TRANSACTIONS TAB:
  -----------------
  TX 1  |  Contract Creation   |  ElectionVoting.sol deployed
  TX 2  |  Contract Call       |  castVote()  — first vote
  TX 3  |  Contract Call       |  castVote()  — second vote
  ...

  Click any transaction to see:
    • Transaction Hash  (same as shown on confirmation page)
    • From / To addresses
    • Gas Used
    • Block Number
    • Events emitted (VoteCast with voter name, role, nomination)

  BLOCKS TAB:
  -----------
  Each vote creates a new block on the local chain.

  CONTRACTS TAB:
  --------------
  Shows ElectionVoting at your deployed address.
  Click it to see all stored votes and nominations.

  EVENTS TAB:
  -----------
  Lists every VoteCast, NominationRegistered event in real time.


====================================================================
TROUBLESHOOTING
====================================================================

  PROBLEM: "node is not recognized as a command"
  FIX: Install Node.js from https://nodejs.org (LTS version)
       Restart CMD after installing.

  PROBLEM: "npm install fails"
  FIX: Run CMD as Administrator:
       Right-click CMD → "Run as administrator"
       Then run 1_setup.bat again.

  PROBLEM: Ganache not reachable / deploy fails
  FIX: - Make sure Ganache GUI is OPEN and shows "RPC SERVER http://127.0.0.1:7545"
       - Check GANACHE_RPC_URL in .env matches exactly
       - Try: curl http://127.0.0.1:7545 in CMD (should return something)

  PROBLEM: "Already voted for this role" error
  FIX: This is CORRECT — the smart contract rejects duplicate votes.
       Use a different test account to vote again.

  PROBLEM: Simulation mode — "[Blockchain] ⚠️ Could not connect"
  FIX: - Ganache not running → open Ganache GUI
       - ELECTION_CONTRACT_ADDRESS blank in .env → run 2_deploy_contract.bat
       - Wrong private key → re-copy from Ganache key icon

  PROBLEM: "ElectionVoting ABI not found"
  FIX: Run 2_deploy_contract.bat — it auto-copies the ABI file.
       Or manually copy:
         election_blockchain\ElectionVoting_ABI.json
         → election_ocr_fixed\ElectionVoting_ABI.json

  PROBLEM: Flask shows no candidates
  FIX: The smart contract also needs nominations registered on-chain.
       Go to Admin → Nominations → Approve some nominations first.
       Approval triggers register_nomination() on the contract.

  PROBLEM: MetaMask widget not showing
  FIX: Install MetaMask extension from https://metamask.io/download
       Refresh the Cast Vote page.
       ethers.js loads from CDN — needs internet connection.


====================================================================
QUICK REFERENCE — KEY VALUES
====================================================================

  Where to find each value:

  GANACHE_RPC_URL
    → Ganache GUI → top of screen → "RPC SERVER http://127.0.0.1:7545"

  GANACHE_PRIVATE_KEY
    → Ganache GUI → click KEY icon (🔑) next to Account 0 → copy key

  ELECTION_CONTRACT_ADDRESS
    → Printed by 2_deploy_contract.bat → copy the 0x... address

  ElectionVoting_ABI.json
    → Auto-generated by 2_deploy_contract.bat → copied to Flask root


====================================================================
NETWORK CHOICE SUMMARY
====================================================================

  GANACHE (this guide) — Best for development
    ✓ Free, no internet needed, instant transactions
    ✓ Full GUI to see transactions, blocks, events
    ✗ Resets when Ganache is closed (data is temporary)

  SEPOLIA TESTNET — Best for sharing / demo
    ✓ Persistent — data stays on public blockchain forever
    ✓ View on Etherscan: https://sepolia.etherscan.io
    ✓ Real MetaMask transactions from any computer
    ✗ Needs internet, free test ETH from faucet, slower (~15s per vote)
    → Change BLOCKCHAIN_NETWORK=sepolia in .env and re-deploy

====================================================================
