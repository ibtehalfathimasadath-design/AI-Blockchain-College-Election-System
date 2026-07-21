# 🔗 Blockchain Integration Guide
## College Election System — Real Ethereum Smart Contract Upgrade

---

## 📁 Files You Received (What Goes Where)

```
blockchain_upgrade/
├── contracts/
│   └── ElectionVoting.sol          → Hardhat project root/contracts/
├── scripts/
│   └── deploy.js                   → Hardhat project root/scripts/
├── utils/
│   └── blockchain.py               → election_ocr_fixed/utils/blockchain.py   ← REPLACE
├── templates/
│   ├── vote_confirmation.html      → election_ocr_fixed/templates/             ← REPLACE
│   ├── admin_votes.html            → election_ocr_fixed/templates/             ← REPLACE
│   └── cast_vote.html              → election_ocr_fixed/templates/             ← REPLACE
├── static/js/
│   └── metamask.js                 → election_ocr_fixed/static/js/            ← NEW FILE
├── hardhat.config.js               → Hardhat project root/
├── package.json                    → Hardhat project root/
├── .env.example                    → election_ocr_fixed/.env.example
├── requirements_blockchain.txt     → (merge into requirements.txt)
└── app_changes.py                  → Reference only — apply changes to app.py
```

---

## 🧰 Prerequisites — Install These First

### 1. Node.js & npm
```bash
# Check if installed
node --version    # Need v18+
npm  --version

# Install from: https://nodejs.org  (choose LTS version)
```

### 2. Python web3 library
```bash
pip install web3==6.15.1 python-dotenv==1.0.1
```

### 3. MetaMask browser extension
- Install from **https://metamask.io/download**
- Create a wallet (save your seed phrase securely)
- You'll use this to interact with the contract from the browser

### 4. Ganache (local Ethereum blockchain — easiest option)
- Download **Ganache GUI** from **https://trufflesuite.com/ganache**
- OR install CLI: `npm install -g ganache`

---

## 📂 Step 1 — Set Up the Hardhat Project

Create a new folder **alongside** your Flask project (not inside it):

```
your-workspace/
├── election_ocr_fixed/     ← existing Flask app
└── election_blockchain/    ← NEW Hardhat project (create this)
```

```bash
# Create and enter the Hardhat project folder
mkdir election_blockchain
cd election_blockchain

# Copy the files you received
cp path/to/blockchain_upgrade/hardhat.config.js  .
cp path/to/blockchain_upgrade/package.json        .
mkdir -p contracts scripts
cp path/to/blockchain_upgrade/contracts/ElectionVoting.sol  contracts/
cp path/to/blockchain_upgrade/scripts/deploy.js             scripts/

# Install Hardhat and dependencies
npm install
```

Verify the install:
```bash
npx hardhat compile
# Expected output: "Compiled 1 Solidity file successfully"
```

---

## 🔑 Step 2 — Configure Environment Variables

### 2a. Copy the .env.example into your Flask project
```bash
cd election_ocr_fixed
cp path/to/blockchain_upgrade/.env.example  .env
```

### 2b. Open `.env` in a text editor

You will fill in **two keys** depending on your chosen network.

---

### OPTION A — Ganache (Recommended for Development)

**Step 1: Open Ganache GUI**
- Launch the Ganache app
- Click **"New Workspace"** → **"Ethereum"** → **Save**
- You'll see 10 pre-funded accounts (each with 100 ETH)

**Step 2: Note these values from the Ganache window:**
- **RPC Server** (e.g., `http://127.0.0.1:7545`)  
- **Chain ID** (shown at top, usually `1337`)

**Step 3: Get a private key**
- Click the 🔑 key icon next to any account
- Copy the private key shown (starts with `0x`)

**Step 4: Fill in `.env`:**
```env
BLOCKCHAIN_NETWORK=ganache
GANACHE_RPC_URL=http://127.0.0.1:7545
GANACHE_PRIVATE_KEY=0xYOUR_GANACHE_PRIVATE_KEY_HERE
```

---

### OPTION B — Sepolia Testnet (Public, Persistent)

**Step 1: Get a free RPC endpoint**
- Go to **https://infura.io** → Sign up → Create project → Copy Sepolia URL
  - Format: `https://sepolia.infura.io/v3/YOUR_PROJECT_ID`
- **OR** use **https://alchemy.com** → Create app → Select Sepolia → Copy HTTPS URL

**Step 2: Export your MetaMask private key**
- Open MetaMask → Click account icon → Account Details → Export Private Key
- Enter your MetaMask password → Copy the key

**Step 3: Get free Sepolia test ETH**
- Go to **https://sepoliafaucet.com** or **https://faucet.quicknode.com/ethereum/sepolia**
- Paste your MetaMask wallet address
- Receive 0.5–1 Sepolia ETH (free)

**Step 4: Fill in `.env`:**
```env
BLOCKCHAIN_NETWORK=sepolia
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
DEPLOYER_PRIVATE_KEY=0xYOUR_METAMASK_PRIVATE_KEY
```

---

## 🚀 Step 3 — Deploy the Smart Contract

### For Ganache:
```bash
cd election_blockchain

# Make sure Ganache is running first!
npx hardhat run scripts/deploy.js --network ganache
```

### For Sepolia:
```bash
npx hardhat run scripts/deploy.js --network sepolia
```

**Expected output:**
```
Deploying with account: 0xYourAccountAddress
Account balance: 100000000000000000000

✅ ElectionVoting deployed to: 0xAbCd1234...
Network: ganache
Deployment info saved to: ./deployment.json
ABI saved to: ./ElectionVoting_ABI.json

─────────────────────────────────────────────────
Next step: copy contractAddress into your .env:
  ELECTION_CONTRACT_ADDRESS=0xAbCd1234...
─────────────────────────────────────────────────
```

---

## 🔧 Step 4 — Update .env with Contract Address

Copy the contract address from the deploy output into your Flask `.env`:

```env
ELECTION_CONTRACT_ADDRESS=0xAbCd1234...YOUR_DEPLOYED_ADDRESS
```

Then copy the ABI file into your Flask project:
```bash
cp election_blockchain/ElectionVoting_ABI.json  election_ocr_fixed/
```

---

## 📝 Step 5 — Replace Flask Project Files

### 5a. Replace blockchain.py
```bash
cp blockchain_upgrade/utils/blockchain.py  election_ocr_fixed/utils/blockchain.py
```

### 5b. Replace templates
```bash
cp blockchain_upgrade/templates/vote_confirmation.html  election_ocr_fixed/templates/
cp blockchain_upgrade/templates/admin_votes.html        election_ocr_fixed/templates/
cp blockchain_upgrade/templates/cast_vote.html          election_ocr_fixed/templates/
```

### 5c. Add MetaMask JavaScript file
```bash
mkdir -p election_ocr_fixed/static/js
cp blockchain_upgrade/static/js/metamask.js  election_ocr_fixed/static/js/
```

---

## ✏️ Step 6 — Apply app.py Changes

Open `election_ocr_fixed/app.py` and make these edits.  
Reference the provided `app_changes.py` for the full code of each section.

### Change 1 — Update imports (near top of app.py)
Find:
```python
from utils.blockchain import Blockchain, get_blockchain
```
Replace with:
```python
from utils.blockchain import Blockchain, get_blockchain, BlockchainClient
```

### Change 2 — Replace cast_vote route
Find the entire `@app.route('/voter/cast-vote', ...)` function and replace it with the `CAST_VOTE_ROUTE` code from `app_changes.py`.

Key additions:
- Calls `bc_client.cast_vote()` for each role
- Stores real `transactionHash` in the `blockchain_hash` DB column
- Puts receipts in session for the confirmation page

### Change 3 — Replace vote_confirmation route
Find `@app.route('/voter/confirmation/<...>')` and replace with `VOTE_CONFIRMATION_ROUTE` from `app_changes.py`.

### Change 4 — Replace blockchain status API
Find `@app.route('/api/blockchain-status')` and replace with `BLOCKCHAIN_STATUS_API` from `app_changes.py`.
Also add the new `@app.route('/api/blockchain-events')` endpoint below it.

### Change 5 — Replace admin_votes route
Find `@app.route('/admin/votes')` and replace with `ADMIN_VOTES_ROUTE` from `app_changes.py`.

### Change 6 — Add blockchain write to nomination approval
In the `update_nomination_status` route, after `db.commit()`, add the `NOMINATION_STATUS_BLOCKCHAIN_SNIPPET` code from `app_changes.py`.

### Change 7 — Pass contract_address to cast_vote template
In the `cast_vote` GET handler, add to the `render_template` call:
```python
return render_template(
    'cast_vote.html',
    candidates_by_role=candidates_by_role,
    contract_address=os.getenv('ELECTION_CONTRACT_ADDRESS', ''),  # ADD THIS
)
```

---

## 🗄️ Step 7 — Update Database Schema

Add the `blockchain_hash` column if it doesn't exist yet.

In your Flask shell or by running this once:
```bash
cd election_ocr_fixed
python3 - <<'EOF'
from utils.database import get_db
import sqlite3

db = sqlite3.connect('election.db')  # adjust path if needed
try:
    db.execute("ALTER TABLE votes ADD COLUMN blockchain_hash TEXT DEFAULT 'pending'")
    db.commit()
    print("Column added successfully")
except sqlite3.OperationalError as e:
    print("Column may already exist:", e)
db.close()
EOF
```

---

## ▶️ Step 8 — Run the Application

### Terminal 1 — Ganache (keep running):
```bash
# GUI: just leave Ganache app open
# OR CLI:
ganache --port 7545 --chainId 1337
```

### Terminal 2 — Flask app:
```bash
cd election_ocr_fixed
python app.py
```

### Open browser:
```
http://localhost:5000
```

---

## ✅ Step 9 — Verify Blockchain is Working

### Test 1 — Check API endpoint
```bash
curl http://localhost:5000/api/blockchain-status
```
Expected response:
```json
{
  "connected": true,
  "network": "ganache",
  "chain_id": 1337,
  "block_number": 5,
  "total_votes": 0,
  "contract": "0xYourContractAddress",
  "simulated": false
}
```

### Test 2 — Cast a vote and check Ganache
1. Log in as a student voter
2. Complete identity verification
3. Cast a vote on the `/voter/cast-vote` page
4. Watch the Ganache GUI → **Transactions tab** — a new transaction appears!
5. The confirmation page shows the real `transactionHash`

### Test 3 — Check admin blockchain explorer
1. Log in as admin
2. Go to **Admin → Votes**
3. Click the **"On-Chain Events"** tab
4. You'll see the real VoteCast events fetched from Ethereum

### Test 4 — Check on-chain events API
```bash
curl http://localhost:5000/api/blockchain-events
```
Returns all `VoteCast` events from the smart contract.

---

## 🦊 Step 10 — MetaMask Wallet Connection (Optional Attestation)

The `cast_vote.html` page now includes a MetaMask widget. To use it:

1. Install MetaMask extension in Chrome/Firefox
2. **For Ganache:** Add Ganache as a custom network in MetaMask:
   - MetaMask → Settings → Networks → Add Network
   - Network Name: `Ganache Local`
   - RPC URL: `http://127.0.0.1:7545`
   - Chain ID: `1337`
   - Currency Symbol: `ETH`
3. **Import a Ganache account into MetaMask:**
   - MetaMask → Import Account → paste the Ganache private key
4. Go to the **Cast Vote** page → click **"Connect MetaMask"**
5. Click **"Sign Vote Attestation"** → MetaMask popup appears → Confirm
6. Your wallet signature is attached to the vote submission

---

## 🔍 How to See the Blockchain Running

### In Ganache GUI:
| Tab | What You See |
|-----|-------------|
| **Transactions** | Every vote as a real ETH transaction with gas, block, hash |
| **Blocks** | New blocks mined when votes are cast |
| **Contracts** | The ElectionVoting contract deployed at your address |
| **Events** | `VoteCast`, `NominationRegistered` events emitted |
| **Logs** | Full ABI call logs for debugging |

### In Sepolia Etherscan:
After deploying to Sepolia, paste your contract address at:  
`https://sepolia.etherscan.io/address/YOUR_CONTRACT_ADDRESS`

You'll see:
- All transactions (votes)
- All events (VoteCast logs)
- Contract source code (if verified)
- Internal transaction trace

To verify source code on Etherscan (optional):
```bash
npx hardhat verify --network sepolia YOUR_CONTRACT_ADDRESS
```

---

## 🐛 Troubleshooting

### "Could not connect to http://127.0.0.1:7545"
- Make sure Ganache is running **before** starting Flask
- Check Ganache's RPC URL matches your `.env`
- The app auto-falls back to simulation mode — check `[Blockchain]` logs in terminal

### "ELECTION_CONTRACT_ADDRESS not set"
- Run the deploy script first: `npx hardhat run scripts/deploy.js --network ganache`
- Copy the printed address into `.env`

### "ElectionVoting ABI not found"
- Make sure `ElectionVoting_ABI.json` is in the Flask project root
- Run: `npx hardhat compile` then re-deploy

### "Already voted for this role" error from contract
- This is correct behavior — the smart contract prevents duplicate votes
- Each voter can only vote once per role (enforced at Solidity level)

### "Nomination not registered" when voting
- Call `bc_client.register_nomination()` for each approved candidate before voting starts
- Or add the nomination registration step to the admin approval route (change 6 above)

### MetaMask shows wrong network
- Make sure you added Ganache as a custom network with Chain ID `1337`
- MetaMask and Flask must both point to the same Ganache instance

### Web3 middleware error on startup
- Make sure you installed: `pip install web3==6.15.1`
- The `ExtraDataToPOAMiddleware` handles Ganache/Sepolia PoA extra data field

---

## 📊 Architecture Summary

```
Browser (Student)
    │
    ├─ GET  /voter/cast-vote   ← Flask renders cast_vote.html
    │       │
    │       └─ metamask.js     ← Connects MetaMask, signs attestation
    │
    └─ POST /voter/cast-vote
            │
            ├─ Flask: write to SQLite (voter_id, nomination_id, 'pending')
            │
            ├─ blockchain.py → web3.py → Ganache/Sepolia
            │       │
            │       └─ ElectionVoting.sol → castVote()
            │               │
            │               ├─ Validates: not double voted, nomination approved
            │               ├─ Stores vote on-chain permanently
            │               └─ Emits: VoteCast event
            │
            ├─ Flask: UPDATE votes SET blockchain_hash = '0xRealTxHash'
            │
            └─ Redirect to /voter/confirmation/0xRealTxHash
                    │
                    └─ Shows real tx receipt, block number, gas used
```

---

## 🔐 Security Properties

| Property | How It's Achieved |
|----------|------------------|
| **Immutability** | Votes stored in Ethereum state — cannot be edited or deleted |
| **No double voting** | Smart contract reverts if voter already voted for same role |
| **Transparency** | All VoteCast events publicly readable on the chain |
| **Auditability** | Every vote has a tx hash verifiable on Etherscan (Sepolia) |
| **Integrity** | Nominations must be admin-approved on-chain before votes accepted |
| **Attestation** | MetaMask signature proves voter controlled their wallet |

---

## 🎯 Quick Reference — Key Values to Replace

| What | Where | Replace With |
|------|-------|-------------|
| `ELECTION_CONTRACT_ADDRESS` | `.env` | Address from deploy output |
| `GANACHE_PRIVATE_KEY` | `.env` | Key from Ganache 🔑 icon |
| `GANACHE_RPC_URL` | `.env` | URL from Ganache "RPC Server" field |
| `SEPOLIA_RPC_URL` | `.env` | Infura/Alchemy endpoint URL |
| `DEPLOYER_PRIVATE_KEY` | `.env` | MetaMask exported private key |
| `ElectionVoting_ABI.json` | Flask root | Generated by `npx hardhat compile` + deploy |
