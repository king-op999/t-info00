# ============================================
# 🔥 AUTO-FAILOVER USERNAME TO CHAT ID
# Acc1 Fail → Acc2 → Acc3 → Cycle ∞
# ============================================
import os
import asyncio
import random
import time
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

app = Flask(__name__)

# ============ 3 ACCOUNTS ============
ACCOUNTS = []

if os.environ.get("SESSION_STRING_1"):
    ACCOUNTS.append({
        "api_id": int(os.environ.get("API_ID_1", "0")),
        "api_hash": os.environ.get("API_HASH_1", ""),
        "session": os.environ.get("SESSION_STRING_1", ""),
        "name": "Acc1"
    })

if os.environ.get("SESSION_STRING_2"):
    ACCOUNTS.append({
        "api_id": int(os.environ.get("API_ID_2", "0")),
        "api_hash": os.environ.get("API_HASH_2", ""),
        "session": os.environ.get("SESSION_STRING_2", ""),
        "name": "Acc2"
    })

if os.environ.get("SESSION_STRING_3"):
    ACCOUNTS.append({
        "api_id": int(os.environ.get("API_ID_3", "0")),
        "api_hash": os.environ.get("API_HASH_3", ""),
        "session": os.environ.get("SESSION_STRING_3", ""),
        "name": "Acc3"
    })

clients = []
fail_counts = {}
success_counts = {}
current_acc = 0

async def init_clients():
    """Sab accounts login karo"""
    global clients
    for acc in ACCOUNTS:
        try:
            client = TelegramClient(
                StringSession(acc["session"]),
                acc["api_id"],
                acc["api_hash"]
            )
            await client.start()
            me = await client.get_me()
            clients.append({
                "client": client,
                "name": acc["name"],
                "phone": me.phone
            })
            fail_counts[acc["name"]] = 0
            success_counts[acc["name"]] = 0
            print(f"✅ {acc['name']}: {me.first_name}")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ {acc['name']}: {str(e)[:50]}")

async def resolve_with_failover(username):
    """Auto-failover between accounts"""
    global current_acc
    
    username = username.replace("@", "").strip()
    
    if not clients:
        return None, "No accounts available"
    
    # Try each account with failover
    for i in range(len(clients)):
        acc_index = (current_acc + i) % len(clients)
        acc = clients[acc_index]
        
        try:
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
            entity = await acc["client"].get_entity(f"@{username}")
            
            # Success! Update counts
            success_counts[acc["name"]] += 1
            current_acc = (acc_index + 1) % len(clients)  # Next account for next request
            
            return {
                "username": username,
                "chat_id": entity.id,
                "name": f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            }, None
            
        except FloodWaitError as e:
            fail_counts[acc["name"]] += 1
            print(f"⏳ {acc['name']} FloodWait {e.seconds}s")
            await asyncio.sleep(min(e.seconds, 30))
            continue
            
        except Exception as e:
            fail_counts[acc["name"]] += 1
            error = str(e)
            
            if "not found" in error.lower():
                return None, "Username not found"
            
            print(f"⚠️ {acc['name']} failed: {error[:50]}")
            await asyncio.sleep(1)
            continue
    
    return None, "All accounts failed or rate limited"

# ============ FLASK ROUTES ============
@app.route('/')
def home():
    return jsonify({
        "api": "/chat?id=@username",
        "example": "/chat?id=@telegram",
        "accounts": len(clients),
        "method": "auto-failover",
        "status": "online" if clients else "no accounts",
        "credit": "@BRONX_ULTRA"
    })

@app.route('/chat')
def chat_id():
    username = request.args.get('id', '')
    
    if not username:
        return jsonify({
            "status": "error",
            "message": "Missing username. Use /chat?id=@username"
        }), 400
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result, error = loop.run_until_complete(resolve_with_failover(username))
        loop.close()
        
        if error:
            return jsonify({
                "status": "error",
                "message": error
            }), 404
        
        if result:
            return jsonify({
                "status": "success",
                "username": result["username"],
                "chat_id": result["chat_id"],
                "name": result["name"]
            })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)[:200]
        }), 500

@app.route('/stats')
def stats():
    return jsonify({
        "accounts": len(clients),
        "success": success_counts,
        "fails": fail_counts,
        "next_account": clients[current_acc]["name"] if clients else "none"
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_clients())
    
    port = int(os.environ.get('PORT', 5000))
    print(f"""
╔══════════════════════════════╗
║ 🔥 AUTO-FAILOVER RESOLVER   ║
║ 📊 {len(clients)} Accounts Active        ║
║ 🔗 /chat?id=@username       ║
║ 🚀 Port: {port}                ║
╚══════════════════════════════╝
""")
    app.run(host='0.0.0.0', port=port)
