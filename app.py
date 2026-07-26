# ============================================
# 🔥 TELEGRAM USERNAME TO CHAT ID
# 3 Accounts • Auto-Failover • Working 100%
# ============================================
from flask import Flask, request, jsonify
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

app = Flask(__name__)

# ============ 3 ACCOUNTS CONFIG ============
ACCOUNTS = [
    {
        "api_id": 33396172,
        "api_hash": "e62d3ab368bd474005cf88e9d59ffbf7",
        "session": "1BVtsOJUBu0k25N9PeIroOvauUGz-jOaiAUZaZA0SZ4Njbiip4pPZhnw10n3w272e7nKg2I7QY_v3fzeOQ7Li3hbN_jil6BIdt7w7lkht5z5GfEnxe7h46Pst3ovOslkFEcjCo539GMX-4fU2rSKm6aRaDoaaAUiNZU5hedOCLc3q4IU6lc4VJ-wmy2QKuEYUcLlEK_ckrPf3NLFRN-_N0sEHP7yJd_qgPVpHAqM5EhltuEgOTN7TJ3LN_aXiNB4bnyW9Ci9uGQvd2ONoVKrpERGivE_mJKXEDSEYltdsjY3Tkc08QQzVQensVIt1_fE2H3jV4l7k1KSzKutx2UjiF9ryiCqunJQ=",
        "name": "Acc1"
    },
    {
        "api_id": 33754080,
        "api_hash": "7883fad751852a4bbe406710f8ea9726",
        "session": "1BVtsOJUBu7MJTKUCHEMaembhiYci7fymaaripvYg88pv7IVjxGd2gDFs4LarqrfJjQVeVsy2oQ8KC78DQp565_7ugxzmVFACUm9t9e0UnqzjDG4_B0KjCFLAA6kzF65gA-47SW__-OvKHClC5rqRx_4YkE1BmSW6MKMVL7bVqSkVkvI3-UHQhM3PJ2TA0yGxUnOR3S8F_6K78a8DBeDPU0Gu2QiQbscqIOPO49-q0sp4ezbo-9uXtw2l0bXlXOiZWh-1GKHT4I7b7tLUJ4UWzABuGsSrWpqXSZ7FGxBKulOlROr857360o3Z27Hw457MwKYXIQJraDKy-OQiBvZv3OOWJhOsXTU=",
        "name": "Acc2"
    },
    {
        "api_id": 21230129,
        "api_hash": "a88b2ec836c8a4038b24239fc14ecc80",
        "session": "1BVtsOJUBu1E865LhfELHIcTtFVIbjxnThR30ucfISUkZSPuh3TQ13QOQhgAEFvvjRJX9WNjAekQ8elVvnDEoytf0jeRnWs0BwCMYVAxQS-TWhaXWwfjXSFlZtgbHvlh3GggbEhpALQ2nVTvVd4YmUZWInXHaidYsW1g2IW0IxHGsA3zDEv0gltlOIMqiuqdIQANsSTpYoM8z5leBMg4_qnqb253WJXp7IpfXtkVO3eBEsWa-ON7BxvPlGELvKqR6jNZEDCYFi85W6NFH_L_T29cVJRmEcjvpTgOOJHMzzMdw8XtQj-v-S4a43zSOM3Ka3VeNexWU4ZM0Lu10RybVvi9DUXLy3Yo=",
        "name": "Acc3"
    },
]

clients = []
current_index = 0

async def init_accounts():
    """Sab accounts login karo"""
    global clients
    for i, acc in enumerate(ACCOUNTS):
        try:
            client = TelegramClient(
                StringSession(acc["session"]),
                acc["api_id"],
                acc["api_hash"]
            )
            await client.connect()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                clients.append(client)
                print(f"✅ Account {i+1}: {me.first_name}")
            else:
                print(f"❌ Account {i+1}: Session expired")
        except Exception as e:
            print(f"❌ Account {i+1}: {e}")

async def get_chat_id(username):
    """Get chat ID with auto-failover"""
    global current_index
    username = username.replace("@", "").strip()
    
    if not clients:
        return None
    
    for _ in range(len(clients)):
        client = clients[current_index]
        current_index = (current_index + 1) % len(clients)
        
        try:
            await asyncio.sleep(0.3)
            entity = await client.get_entity(f"@{username}")
            
            return {
                "username": username,
                "chat_id": entity.id,
                "name": f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            }
            
        except FloodWaitError as e:
            print(f"⏳ FloodWait {e.seconds}s")
            await asyncio.sleep(min(e.seconds, 10))
            continue
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            continue
    
    return None

# ============ ROUTES ============
@app.route('/')
def home():
    return jsonify({
        "api": "/chat?id=@username",
        "example": "/chat?id=@telegram",
        "accounts": len(clients),
        "status": "online" if clients else "no accounts"
    })

@app.route('/chat')
def chat():
    username = request.args.get('id', '')
    if not username:
        return jsonify({"status": "error", "message": "Missing ?id=@username"}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_chat_id(username))
    loop.close()
    
    if result:
        return jsonify({"status": "success", **result})
    return jsonify({"status": "error", "message": "Not found"}), 404

@app.route('/health')
def health():
    return jsonify({"status": "ok", "accounts": len(clients)})

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_accounts())
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 {len(clients)} Accounts Ready!")
    app.run(host='0.0.0.0', port=port)
