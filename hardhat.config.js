require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },

  networks: {
    // ── Local Ganache (default for development) ──────────────────────
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      // Paste any Ganache account private key below, OR use .env
      accounts: process.env.GANACHE_PRIVATE_KEY
        ? [process.env.GANACHE_PRIVATE_KEY]
        : [],
    },

    // ── Sepolia Testnet ───────────────────────────────────────────────
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "https://rpc.sepolia.org",
      chainId: 11155111,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },

    // ── Hardhat built-in node (instant, no setup) ────────────────────
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
  },

  // Etherscan verification (optional, only needed for public testnets)
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY || "",
  },

  paths: {
    sources:   "./contracts",
    tests:     "./test",
    cache:     "./cache",
    artifacts: "./artifacts",
  },
};
