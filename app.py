# ============================================
# 🔥 SIMPLE USERNAME TO CHAT ID
# Bas Session Strings Dalo • 100% Working
# ============================================
import asyncio
import random
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

# ============ APNI SESSION STRINGS YAHAN DALO ============
SESSION_STRINGS = [
    "1BVtsOJUBu0k25N9PeIroOvauUGz-jOaiAUZaZA0SZ4Njbiip4pPZhnw10n3w272e7nKg2I7QY_v3fzeOQ7Li3hbN_jil6BIdt7w7lkht5z5GfEnxe7h46Pst3ovOslkFEcjCo539GMX-4fU2rSKm6aRaDoaaAUiNZU5hedOCLc3q4IU6lc4VJ-wmy2QKuEYUcLlEK_ckrPf3NLFRN-_N0sEHP7yJd_qgPVpHAqM5EhltuEgOTN7TJ3LN_aXiNB4bnyW9Ci9uGQvd2ONoVKrpERGivE_mJKXEDSEYltdsjY3Tkc08QQzVQensVIt1_fE2H3jV4l7k1KSzKutx2UjiF9ryiCqunJQ=",  # Account 1 ki session string
    "1BVtsOJUBu7MJTKUCHEMaembhiYci7fymaaripvYg88pv7IVjxGd2gDFs4LarqrfJjQVeVsy2oQ8KC78DQp565_7ugxzmVFACUm9t9e0UnqzjDG4_B0KjCFLAA6kzF65gA-47SW__-OvKHClC5rqRx_4YkE1BmSW6MKMVL7bVqSkVkvI3-UHQhM3PJ2TA0yGxUnOR3S8F_6K78a8DBeDPU0Gu2QiQbscqIOPO49-q0sp4ezbo-9uXtw2l0bXlXOiZWh-1GKHT4I7b7tLUJ4UWzABuGsSrWpqXSZ7FGxBKulOlROr857360o3Z27Hw457MwKYXIQJraDKy-OQiBvZv3OOWJhOsXTU=",  # Account 2 ki session string  
    "1BVtsOJUBu1E865LhfELHIcTtFVIbjxnThR30ucfISUkZSPuh3TQ13QOQhgAEFvvjRJX9WNjAekQ8elVvnDEoytf0jeRnWs0BwCMYVAxQS-TWhaXWwfjXSFlZtgbHvlh3GggbEhpALQ2nVTvVd4YmUZWInXHaidYsW1g2IW0IxHGsA3zDEv0gltlOIMqiuqdIQANsSTpYoM8z5leBMg4_qnqb253WJXp7IpfXtkVO3eBEsWa-ON7BxvPlGELvKqR6jNZEDCYFi85W6NFH_L_T29cVJRmEcjvpTgOOJHMzzMdw8XtQj-v-S4a43zSOM3Ka3VeNexWU4ZM0Lu10RybVvi9DUXLy3Yo=",  # Account 3 ki session string
]

# ============ API CREDENTIALS ============
API_CREDENTIALS = [
    {"api_id": 33396172, "api_hash": "e62d3ab368bd474005cf88e9d59ffbf7"},
    {"api_id": 33754080, "api_hash": "7883fad751852a4bbe406710f8ea9726"},
    {"api_id": 21230129, "api_hash": "a88b2ec836c8a4038b24239fc14ecc80"},
]

clients = []
current = 0

async def start_clients():
    global clients
    for i in range(len(SESSION_STRINGS)):
        try:
            client = TelegramClient(
                StringSession(SESSION_STRINGS[i]),
                API_CREDENTIALS[i]["api_id"],
                API_CREDENTIALS[i]["api_hash"]
            )
            await client.start()
            me = await client.get_me()
            clients.append(client)
            print(f"✅ Account {i+1}: {me.first_name}")
        except Exception as e:
            print(f"❌ Account {i+1}: {e}")

async def get_id(username):
    global current
    username = username.replace("@", "").strip()
    
    if not clients:
        return None
    
    for _ in range(len(clients)):
        client = clients[current]
        current = (current + 1) % len(clients)
        
        try:
            await asyncio.sleep(0.5)
            user = await client.get_entity(f"@{username}")
            return {
                "username": username,
                "chat_id": user.id,
                "name": f"{user.first_name or ''} {user.last_name or ''}".strip()
            }
        except:
            continue
    
    return None

@app.route('/')
def home():
    return jsonify({
        "api": "/chat?id=@username",
        "accounts": len(clients),
        "credit": "@BRONX_ULTRA"
    })

@app.route('/chat')
def chat():
    username = request.args.get('id', '')
    if not username:
        return jsonify({"error": "Missing ?id=@username"}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_id(username))
    loop.close()
    
    if result:
        return jsonify({"status": "success", **result})
    return jsonify({"status": "error", "message": "Not found"}), 404

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_clients())
    
    import os
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)
