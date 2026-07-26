from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import asyncio
import os
import time
from datetime import datetime, timedelta

app = Flask(__name__)
CREDIT = "@BRONX_ULTRA"

# ============================================
# 3 CONFIGURATIONS - ADD YOUR CREDENTIALS HERE
# ============================================
CONFIGS = [
    {
        "id": 1,
        "name": "Primary",
        "api_id": int(os.environ.get('API_ID_1', '33396172')),
        "api_hash": os.environ.get('API_HASH_1', 'e62d3ab368bd474005cf88e9d59ffbf7'),
        "session_string": os.environ.get('SESSION_STRING_1', '1BVtsOJUBu0k25N9PeIroOvauUGz-jOaiAUZaZA0SZ4Njbiip4pPZhnw10n3w272e7nKg2I7QY_v3fzeOQ7Li3hbN_jil6BIdt7w7lkht5z5GfEnxe7h46Pst3ovOslkFEcjCo539GMX-4fU2rSKm6aRaDoaaAUiNZU5hedOCLc3q4IU6lc4VJ-wmy2QKuEYUcLlEK_ckrPf3NLFRN-_N0sEHP7yJd_qgPVpHAqM5EhltuEgOTN7TJ3LN_aXiNB4bnyW9Ci9uGQvd2ONoVKrpERGivE_mJKXEDSEYltdsjY3Tkc08QQzVQensVIt1_fE2H3jV4l7k1KSzKutx2UjiF9ryiCqunJQ='),
        "flood_until": None,
        "request_count": 0,
        "client": None
    },
    {
        "id": 2,
        "name": "Secondary",
        "api_id": int(os.environ.get('API_ID_2', '33754080')),
        "api_hash": os.environ.get('API_HASH_2', '7883fad751852a4bbe406710f8ea9726'),
        "session_string": os.environ.get('SESSION_STRING_2', '1BVtsOJUBu7MJTKUCHEMaembhiYci7fymaaripvYg88pv7IVjxGd2gDFs4LarqrfJjQVeVsy2oQ8KC78DQp565_7ugxzmVFACUm9t9e0UnqzjDG4_B0KjCFLAA6kzF65gA-47SW__-OvKHClC5rqRx_4YkE1BmSW6MKMVL7bVqSkVkvI3-UHQhM3PJ2TA0yGxUnOR3S8F_6K78a8DBeDPU0Gu2QiQbscqIOPO49-q0sp4ezbo-9uXtw2l0bXlXOiZWh-1GKHT4I7b7tLUJ4UWzABuGsSrWpqXSZ7FGxBKulOlROr857360o3Z27Hw457MwKYXIQJraDKy-OQiBvZv3OOWJhOsXTU='),
        "flood_until": None,
        "request_count": 0,
        "client": None
    },
    {
        "id": 3,
        "name": "Backup",
        "api_id": int(os.environ.get('API_ID_3', '21230129')),
        "api_hash": os.environ.get('API_HASH_3', 'a88b2ec836c8a4038b24239fc14ecc80'),
        "session_string": os.environ.get('SESSION_STRING_3', '1BVtsOJUBu1E865LhfELHIcTtFVIbjxnThR30ucfISUkZSPuh3TQ13QOQhgAEFvvjRJX9WNjAekQ8elVvnDEoytf0jeRnWs0BwCMYVAxQS-TWhaXWwfjXSFlZtgbHvlh3GggbEhpALQ2nVTvVd4YmUZWInXHaidYsW1g2IW0IxHGsA3zDEv0gltlOIMqiuqdIQANsSTpYoM8z5leBMg4_qnqb253WJXp7IpfXtkVO3eBEsWa-ON7BxvPlGELvKqR6jNZEDCYFi85W6NFH_L_T29cVJRmEcjvpTgOOJHMzzMdw8XtQj-v-S4a43zSOM3Ka3VeNexWU4ZM0Lu10RybVvi9DUXLy3Yo='),
        "flood_until": None,
        "request_count": 0,
        "client": None
    }
]

# Cache
cache = {}
CACHE_TTL = 86400

# Event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Active config index
active_config = 0


# ============================================
# GET WORKING CONFIG
# ============================================
def get_working_config():
    """Get next working config that's not flooded"""
    global active_config
    
    for i in range(3):
        idx = (active_config + i) % 3
        cfg = CONFIGS[idx]
        
        if cfg['client'] is None:
            continue
        
        if cfg['flood_until'] and time.time() < cfg['flood_until']:
            continue
        
        active_config = idx
        return cfg
    
    return None


# ============================================
# TELEGRAM ENTITY FETCH
# ============================================
async def get_entity_with_config(cfg, username, retry_count=0):
    """Get entity using specific config"""
    clean = username.replace("@", "")
    
    try:
        await cfg['client'].connect()
        
        if not await cfg['client'].is_user_authorized():
            raise Exception(f"Config {cfg['id']} not authorized")
        
        entity = await cfg['client'].get_entity(f"@{clean}")
        cfg['request_count'] += 1
        return entity, cfg
        
    except FloodWaitError as e:
        cfg['flood_until'] = time.time() + e.seconds + 5
        print(f"⏰ Config {cfg['id']} flood: {e.seconds}s")
        
        if retry_count < 2:
            # Try next config
            next_cfg = get_working_config()
            if next_cfg and next_cfg['id'] != cfg['id']:
                return await get_entity_with_config(next_cfg, username, retry_count + 1)
        
        raise Exception(f"All configs flooded! Wait {e.seconds}s")
    
    except Exception as e:
        raise e


# ============================================
# CACHE FUNCTIONS
# ============================================
def get_cached_result(username):
    if username in cache:
        result, timestamp = cache[username]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return result
    return None

def set_cached_result(username, result):
    cache[username] = (result, datetime.now())


# ============================================
# FLASK ROUTES
# ============================================
@app.route('/')
def home():
    config_status = ""
    for c in CONFIGS:
        if c['client']:
            status = "✅ Ready" 
            if c['flood_until'] and time.time() < c['flood_until']:
                wait = int(c['flood_until'] - time.time())
                status = f"⏰ Flood {wait}s"
        else:
            status = "❌ Not Init"
        config_status += f"Config {c['id']} ({c['name']}): {status} | Reqs: {c['request_count']}<br>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BRONX ULTRA API</title>
        <style>
            body {{ background: #000; color: #0ff; font-family: monospace; text-align: center; padding: 50px; }}
            .box {{ background: #111; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px; text-align: left; }}
            code {{ background: #000; padding: 10px; color: #fa0; display: block; margin: 10px 0; border-radius: 5px; }}
            input {{ width: 80%; padding: 12px; background: #222; border: 1px solid #0ff; color: #fff; border-radius: 5px; margin: 10px 0; }}
            button {{ padding: 12px 30px; background: #0ff; color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>🆔 BRONX ULTRA API</h1>
        <h3>3 CONFIGS AUTO-ROTATE</h3>
        
        <div class="box">
            <strong>📊 Config Status:</strong><br>
            {config_status}
        </div>
        
        <code>GET /chatid?username=USERNAME</code>
        
        <input type="text" id="username" placeholder="Enter username...">
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
        return jsonify({"status": "error", "message": "Missing username", "credit": CREDIT}), 400
    
    # Check cache
    cached_result = get_cached_result(username)
    if cached_result:
        cached_result['cache_hit'] = True
        cached_result['credit'] = CREDIT
        return jsonify(cached_result)
    
    # Get working config
    cfg = get_working_config()
    if not cfg:
        return jsonify({
            "status": "error",
            "message": "No working config available! Check credentials.",
            "credit": CREDIT
        }), 503
    
    try:
        entity, used_cfg = loop.run_until_complete(get_entity_with_config(cfg, username))
        clean = username.replace("@", "")
        
        result = {
            "status": "success",
            "chat_id": entity.id,
            "username": getattr(entity, 'username', clean),
            "config_used": f"Config {used_cfg['id']} ({used_cfg['name']})",
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
        
        set_cached_result(username, result)
        result['cache_hit'] = False
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)[:300],
            "credit": CREDIT
        }), 404


@app.route('/clear-cache')
def clear_cache():
    cache.clear()
    return jsonify({"status": "success", "message": "Cache cleared", "credit": CREDIT})


@app.route('/cache-stats')
def cache_stats():
    return jsonify({
        "status": "success",
        "cached_usernames": len(cache),
        "cache_ttl_hours": CACHE_TTL // 3600,
        "total_requests": sum([c['request_count'] for c in CONFIGS]),
        "credit": CREDIT
    })


@app.route('/health')
def health():
    ready = sum([1 for c in CONFIGS if c['client'] is not None])
    return jsonify({
        "status": "ok" if ready > 0 else "no_configs",
        "ready_configs": ready,
        "total_configs": len(CONFIGS),
        "cache_size": len(cache),
        "credit": CREDIT
    })


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    async def init():
        for cfg in CONFIGS:
            try:
                if not cfg['api_id'] or not cfg['api_hash'] or not cfg['session_string']:
                    print(f"⚠️ Config {cfg['id']} ({cfg['name']}): No credentials!")
                    continue
                
                client = TelegramClient(
                    StringSession(cfg['session_string']),
                    cfg['api_id'],
                    cfg['api_hash'],
                    loop=loop
                )
                await client.connect()
                
                if await client.is_user_authorized():
                    cfg['client'] = client
                    print(f"✅ Config {cfg['id']} ({cfg['name']}): Ready!")
                else:
                    print(f"❌ Config {cfg['id']} ({cfg['name']}): Session expired!")
                    await client.disconnect()
                    
            except Exception as e:
                print(f"❌ Config {cfg['id']} ({cfg['name']}): {str(e)[:100]}")
    
    loop.run_until_complete(init())
    
    ready = sum([1 for c in CONFIGS if c['client'] is not None])
    print(f"\n📊 {ready}/3 Configurations Ready\n")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
