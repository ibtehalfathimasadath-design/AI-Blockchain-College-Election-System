/**
 * deploy.js — Deploy ElectionVoting to Ganache or Sepolia
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network ganache
 *   npx hardhat run scripts/deploy.js --network sepolia
 *   npx hardhat run scripts/deploy.js --network localhost   (hardhat node)
 */

const hre = require("hardhat");
const fs  = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);
  console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  // Deploy contract
  const Election = await hre.ethers.getContractFactory("ElectionVoting");
  const election = await Election.deploy();
  await election.waitForDeployment();

  const contractAddress = await election.getAddress();
  console.log("\n✅ ElectionVoting deployed to:", contractAddress);
  console.log("Network:", hre.network.name);

  // Save deployment info so Flask can read it
  const deployInfo = {
    contractAddress,
    network:        hre.network.name,
    chainId:        hre.network.config.chainId,
    deployedAt:     new Date().toISOString(),
    deployerAddress: deployer.address,
  };

  // Write to root of the Flask project (adjust path if needed)
  const outPath = path.join(__dirname, "..", "deployment.json");
  fs.writeFileSync(outPath, JSON.stringify(deployInfo, null, 2));
  console.log("Deployment info saved to:", outPath);

  // Also copy the ABI to a convenient location
  const artifactPath = path.join(
    __dirname, "..", "artifacts", "contracts", "ElectionVoting.sol", "ElectionVoting.json"
  );
  if (fs.existsSync(artifactPath)) {
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const abiOut = path.join(__dirname, "..", "ElectionVoting_ABI.json");
    fs.writeFileSync(abiOut, JSON.stringify(artifact.abi, null, 2));
    console.log("ABI saved to:", abiOut);
  }

  console.log("\n─────────────────────────────────────────────────");
  console.log("Next step: copy contractAddress into your .env:");
  console.log(`  ELECTION_CONTRACT_ADDRESS=${contractAddress}`);
  console.log("─────────────────────────────────────────────────\n");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
