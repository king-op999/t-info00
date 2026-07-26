from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import asyncio
import os
import time
from datetime import datetime, timedelta
import threading

app = Flask(__name__)

CREDIT = "@BRONX_ULTRA"

# ============================================
# 3 CONFIGURATIONS
# ============================================
CONFIGURATIONS = [
    {
        "id": 1,
        "api_id": int(os.environ.get('API_ID_1', '33396172')),
        "api_hash": os.environ.get('API_HASH_1', 'e62d3ab368bd474005cf88e9d59ffbf7'),
        "session_string": os.environ.get('SESSION_STRING_1', '1BVtsOJUBu0k25N9PeIroOvauUGz-jOaiAUZaZA0SZ4Njbiip4pPZhnw10n3w272e7nKg2I7QY_v3fzeOQ7Li3hbN_jil6BIdt7w7lkht5z5GfEnxe7h46Pst3ovOslkFEcjCo539GMX-4fU2rSKm6aRaDoaaAUiNZU5hedOCLc3q4IU6lc4VJ-wmy2QKuEYUcLlEK_ckrPf3NLFRN-_N0sEHP7yJd_qgPVpHAqM5EhltuEgOTN7TJ3LN_aXiNB4bnyW9Ci9uGQvd2ONoVKrpERGivE_mJKXEDSEYltdsjY3Tkc08QQzVQensVIt1_fE2H3jV4l7k1KSzKutx2UjiF9ryiCqunJQ='),
        "name": "Primary",
        "client": None,
        "flood_until": None,
        "request_count": 0,
        "is_active": True,
        "initialized": False
    },
    {
        "id": 2,
        "api_id": int(os.environ.get('API_ID_2', '33754080')),
        "api_hash": os.environ.get('API_HASH_2', '7883fad751852a4bbe406710f8ea9726'),
        "session_string": os.environ.get('SESSION_STRING_2', '1BVtsOJUBu7MJTKUCHEMaembhiYci7fymaaripvYg88pv7IVjxGd2gDFs4LarqrfJjQVeVsy2oQ8KC78DQp565_7ugxzmVFACUm9t9e0UnqzjDG4_B0KjCFLAA6kzF65gA-47SW__-OvKHClC5rqRx_4YkE1BmSW6MKMVL7bVqSkVkvI3-UHQhM3PJ2TA0yGxUnOR3S8F_6K78a8DBeDPU0Gu2QiQbscqIOPO49-q0sp4ezbo-9uXtw2l0bXlXOiZWh-1GKHT4I7b7tLUJ4UWzABuGsSrWpqXSZ7FGxBKulOlROr857360o3Z27Hw457MwKYXIQJraDKy-OQiBvZv3OOWJhOsXTU='),
        "name": "Secondary",
        "client": None,
        "flood_until": None,
        "request_count": 0,
        "is_active": True,
        "initialized": False
    },
    {
        "id": 3,
        "api_id": int(os.environ.get('API_ID_3', '21230129')),
        "api_hash": os.environ.get('API_HASH_3', 'a88b2ec836c8a4038b24239fc14ecc80'),
        "session_string": os.environ.get("1BVtsOJUBu1E865LhfELHIcTtFVIbjxnThR30ucfISUkZSPuh3TQ13QOQhgAEFvvjRJX9WNjAekQ8elVvnDEoytf0jeRnWs0BwCMYVAxQS-TWhaXWwfjXSFlZtgbHvlh3GggbEhpALQ2nVTvVd4YmUZWInXHaidYsW1g2IW0IxHGsA3zDEv0gltlOIMqiuqdIQANsSTpYoM8z5leBMg4_qnqb253WJXp7IpfXtkVO3eBEsWa-ON7BxvPlGELvKqR6jNZEDCYFi85W6NFH_L_T29cVJRmEcjvpTgOOJHMzzMdw8XtQj-v-S4a43zSOM3Ka3VeNexWU4ZM0Lu10RybVvi9DUXLy3Yo=', ''),
        "name": "Backup",
        "client": None,
        "flood_until": None,
        "request_count": 0,
        "is_active": True,
        "initialized": False
    }
]

current_config_index = 0
config_lock = threading.Lock()
cache = {}
CACHE_TTL = 86400

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


# ============================================
# INITIALIZE SINGLE CLIENT
# ============================================
async def init_single_client(config):
    """Initialize one client with proper error handling"""
    try:
        if not config['api_id'] or not config['api_hash'] or not config['session_string']:
            print(f"⚠️ Config {config['id']} ({config['name']}): Missing credentials!")
            return False
        
        client = TelegramClient(
            StringSession(config['session_string']),
            config['api_id'],
            config['api_hash'],
            loop=loop,
            connection_retries=3,
            retry_delay=1
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            config['client'] = client
            config['initialized'] = True
            print(f"✅ Config {config['id']} ({config['name']}): Ready!")
            return True
        else:
            print(f"❌ Config {config['id']} ({config['name']}): Session expired! Regenerate string.")
            await client.disconnect()
            return False
            
    except Exception as e:
        print(f"❌ Config {config['id']} ({config['name']}): Init failed - {str(e)[:100]}")
        return False


# ============================================
# GET ACTIVE CONFIG
# ============================================
def get_active_config():
    """Get working configuration"""
    global current_config_index
    
    with config_lock:
        # Try current first
        for i in range(3):
            idx = (current_config_index + i) % 3
            config = CONFIGURATIONS[idx]
            
            # Check if initialized and not flooded
            if config['initialized'] and config['client']:
                if config['flood_until'] and datetime.now() < config['flood_until']:
                    continue  # Skip flooded config
                
                current_config_index = idx
                return config, None
        
        # No config available
        return None, "No active configuration available. Check credentials or wait for flood limit."


def set_config_flood(config, seconds):
    """Mark config as rate limited"""
    config['flood_until'] = datetime.now() + timedelta(seconds=seconds + 5)
    print(f"⏰ Config {config['id']} ({config['name']}): Flood wait {seconds}s")
    
    def reactivate():
        time.sleep(seconds + 5)
        config['flood_until'] = None
        print(f"✅ Config {config['id']} ({config['name']}): Reactivated!")
    
    threading.Thread(target=reactivate, daemon=True).start()


# ============================================
# CACHE
# ============================================
def get_cached(username):
    if username in cache:
        result, timestamp = cache[username]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return result
    return None

def set_cached(username, result):
    cache[username] = (result, datetime.now())


# ============================================
# TELEGRAM ENTITY FETCH
# ============================================
async def fetch_entity(config, username):
    """Fetch entity with config"""
    clean = username.replace("@", "").strip()
    
    if not config['client']:
        raise Exception("Client not initialized")
    
    try:
        # Ensure connected
        if not config['client'].is_connected():
            await config['client'].connect()
        
        entity = await config['client'].get_entity(f"@{clean}")
        config['request_count'] += 1
        return entity
        
    except FloodWaitError as e:
        set_config_flood(config, e.seconds)
        raise Exception(f"Flood wait: {e.seconds}s. Auto-rotating...")
    except Exception as e:
        raise Exception(f"Failed: {str(e)[:200]}")


# ============================================
# FLASK ROUTES
# ============================================
@app.route('/')
def home():
    status_html = ""
    for c in CONFIGURATIONS:
        status = "✅ Ready" if c['initialized'] else "❌ Not Init"
        if c['flood_until'] and datetime.now() < c['flood_until']:
            status = f"⏰ Flood until {c['flood_until'].strftime('%H:%M:%S')}"
        status_html += f"Config {c['id']} ({c['name']}): {status} | Reqs: {c['request_count']}<br>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BRONX ULTRA API</title>
        <style>
            body {{ background: #000; color: #0ff; font-family: monospace; text-align: center; padding: 50px; }}
            .box {{ background: #111; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px; text-align: left; }}
            code {{ background: #000; padding: 10px; color: #fa0; display: block; margin: 10px 0; border-radius: 5px; }}
            .green {{ color: #0f0; }}
            .red {{ color: #f00; }}
            .yellow {{ color: #ff0; }}
            input {{ width: 80%; padding: 12px; background: #222; border: 1px solid #0ff; color: #fff; border-radius: 5px; margin: 10px 0; }}
            button {{ padding: 12px 30px; background: #0ff; color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>🆔 BRONX ULTRA API</h1>
        <h3>3 CONFIGS AUTO-ROTATE</h3>
        
        <div class="box">
            <strong>📊 Config Status:</strong><br>
            <span class="green">{status_html}</span>
        </div>
        
        <input type="text" id="username" placeholder="Enter Telegram username...">
        <button onclick="lookup()">🔍 GET CHAT ID</button>
        
        <div class="box" id="result" style="display:none;">
            <pre id="resultData" style="color:#0f0;"></pre>
        </div>
        
        <p style="color:#555; margin-top:20px;">{CREDIT}</p>
        <p style="color:#0f0;">🔥 3 CONFIGS | AUTO-ROTATE | 24H CACHE</p>
        
        <script>
        async function lookup() {{
            var u = document.getElementById('username').value.trim();
            if (!u) return alert('Enter username!');
            var d = document.getElementById('result');
            var p = document.getElementById('resultData');
            d.style.display = 'block';
            p.style.color = '#ff0';
            p.textContent = '🔍 Fetching...';
            try {{
                var r = await fetch('/chatid?username=' + encodeURIComponent(u));
                var j = await r.json();
                p.style.color = '#0f0';
                p.textContent = JSON.stringify(j, null, 2);
            }} catch(e) {{
                p.style.color = '#f00';
                p.textContent = 'Error: ' + e.message;
            }}
        }}
        </script>
    </body>
    </html>
    """


@app.route('/chatid')
def chatid():
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({"status": "error", "message": "Username required", "credit": CREDIT}), 400
    
    # Check cache
    cached = get_cached(username)
    if cached:
        cached['cache'] = True
        cached['credit'] = CREDIT
        return jsonify(cached)
    
    # Get active config
    config, error = get_active_config()
    if not config:
        return jsonify({"status": "error", "message": error, "credit": CREDIT}), 503
    
    try:
        entity = loop.run_until_complete(fetch_entity(config, username))
        
        clean = username.replace("@", "")
        result = {
            "status": "success",
            "chat_id": entity.id,
            "username": getattr(entity, 'username', clean),
            "config_used": f"Config {config['id']} ({config['name']})",
            "credit": CREDIT
        }
        
        if hasattr(entity, 'broadcast') and entity.broadcast:
            result["type"] = "channel"
            result["title"] = getattr(entity, 'title', '')
        elif hasattr(entity, 'title'):
            result["type"] = "group"
            result["title"] = entity.title
        else:
            result["type"] = "user"
            result["first_name"] = getattr(entity, 'first_name', '')
            result["last_name"] = getattr(entity, 'last_name', '')
        
        set_cached(username, result)
        result['cache'] = False
        return jsonify(result)
        
    except Exception as e:
        error_msg = str(e)
        
        # Try rotating to next config
        if "Flood wait" in error_msg or "Failed" in error_msg:
            config, _ = get_active_config()
            if config:
                try:
                    entity = loop.run_until_complete(fetch_entity(config, username))
                    clean = username.replace("@", "")
                    result = {
                        "status": "success",
                        "chat_id": entity.id,
                        "username": getattr(entity, 'username', clean),
                        "config_used": f"Config {config['id']} ({config['name']}) [ROTATED]",
                        "credit": CREDIT
                    }
                    
                    if hasattr(entity, 'title'):
                        result["title"] = entity.title
                    else:
                        result["first_name"] = getattr(entity, 'first_name', '')
                    
                    set_cached(username, result)
                    result['cache'] = False
                    result['rotated'] = True
                    return jsonify(result)
                    
                except Exception as e2:
                    error_msg = str(e2)
        
        return jsonify({
            "status": "error",
            "message": error_msg[:300],
            "credit": CREDIT
        }), 404


@app.route('/config-status')
def config_status():
    status = []
    for c in CONFIGURATIONS:
        status.append({
            "id": c['id'],
            "name": c['name'],
            "initialized": c['initialized'],
            "active": c['is_active'],
            "flood_until": c['flood_until'].strftime('%H:%M:%S') if c['flood_until'] else None,
            "requests": c['request_count']
        })
    
    return jsonify({
        "configs": status,
        "active_index": current_config_index,
        "active_name": CONFIGURATIONS[current_config_index]['name'],
        "credit": CREDIT
    })


@app.route('/health')
def health():
    ready = sum([1 for c in CONFIGURATIONS if c['initialized']])
    return jsonify({
        "status": "ok" if ready > 0 else "no_configs",
        "ready_configs": ready,
        "total_configs": len(CONFIGURATIONS),
        "cache_size": len(cache),
        "credit": CREDIT
    })


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════╗
    ║   BRONX ULTRA API               ║
    ║   3 CONFIGS AUTO-ROTATE         ║
    ╚══════════════════════════════════╝
    """)
    
    # Initialize all configs
    async def init_all():
        for config in CONFIGURATIONS:
            success = await init_single_client(config)
            if success:
                print(f"✅ Config {config['id']} ({config['name']}) - READY")
            else:
                print(f"❌ Config {config['id']} ({config['name']}) - FAILED")
    
    loop.run_until_complete(init_all())
    
    ready = sum([1 for c in CONFIGURATIONS if c['initialized']])
    print(f"\n📊 {ready}/3 Configurations Ready\n")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
