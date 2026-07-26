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
# 3 CONFIGURATIONS - AUTO ROTATION
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
        "is_active": True
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
        "is_active": True
    },
    {
        "id": 3,
        "api_id": int(os.environ.get('API_ID_3', '21230129')),
        "api_hash": os.environ.get('API_HASH_3', 'a88b2ec836c8a4038b24239fc14ecc80'),
        "session_string": os.environ.get('SESSION_STRING_3', '1BVtsOJUBu1E865LhfELHIcTtFVIbjxnThR30ucfISUkZSPuh3TQ13QOQhgAEFvvjRJX9WNjAekQ8elVvnDEoytf0jeRnWs0BwCMYVAxQS-TWhaXWwfjXSFlZtgbHvlh3GggbEhpALQ2nVTvVd4YmUZWInXHaidYsW1g2IW0IxHGsA3zDEv0gltlOIMqiuqdIQANsSTpYoM8z5leBMg4_qnqb253WJXp7IpfXtkVO3eBEsWa-ON7BxvPlGELvKqR6jNZEDCYFi85W6NFH_L_T29cVJRmEcjvpTgOOJHMzzMdw8XtQj-v-S4a43zSOM3Ka3VeNexWU4ZM0Lu10RybVvi9DUXLy3Yo='),
        "name": "Backup",
        "client": None,
        "flood_until": None,
        "request_count": 0,
        "is_active": True
    }
]

# Active config index
current_config_index = 0
config_lock = threading.Lock()

# Cache
cache = {}
CACHE_TTL = 86400  # 24 hours

# Create event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ============================================
# CONFIGURATION MANAGER
# ============================================
def get_active_config():
    """Get currently active configuration"""
    global current_config_index
    
    with config_lock:
        # Try current config first
        config = CONFIGURATIONS[current_config_index]
        
        # Check if current config is in flood wait
        if config['flood_until'] and datetime.now() < config['flood_until']:
            # Current config is rate limited, rotate to next
            rotated = False
            for i in range(3):
                current_config_index = (current_config_index + 1) % 3
                new_config = CONFIGURATIONS[current_config_index]
                
                if new_config['flood_until'] is None or datetime.now() >= new_config['flood_until']:
                    config = new_config
                    rotated = True
                    break
            
            if not rotated:
                # All configs are rate limited
                min_wait = min([c['flood_until'] for c in CONFIGURATIONS if c['flood_until']])
                wait_seconds = (min_wait - datetime.now()).seconds if min_wait else 60
                return None, f"⏰ All accounts rate limited! Wait {wait_seconds} seconds."
        
        return config, None

def set_config_flood(config, seconds):
    """Mark config as rate limited"""
    config['flood_until'] = datetime.now() + timedelta(seconds=seconds + 5)
    config['is_active'] = False
    
    # Schedule reactivation
    def reactivate():
        time.sleep(seconds + 5)
        config['is_active'] = True
        config['flood_until'] = None
    
    threading.Thread(target=reactivate, daemon=True).start()

def initialize_config(config):
    """Initialize a single configuration"""
    try:
        client = TelegramClient(
            StringSession(config['session_string']),
            config['api_id'],
            config['api_hash'],
            loop=loop
        )
        config['client'] = client
        return True
    except Exception as e:
        print(f"❌ Config {config['id']} init failed: {e}")
        return False

async def get_entity_with_config(config, username):
    """Get entity using specific config with retry"""
    clean = username.replace("@", "")
    
    try:
        await config['client'].connect()
        
        if not await config['client'].is_user_authorized():
            raise Exception(f"Config {config['id']} not authorized")
        
        entity = await config['client'].get_entity(f"@{clean}")
        config['request_count'] += 1
        return entity
        
    except FloodWaitError as e:
        set_config_flood(config, e.seconds)
        raise FloodWaitError(e.seconds)
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
    config_status = []
    for c in CONFIGURATIONS:
        status = "✅ Active" if c['is_active'] else f"⏰ Flood until {c['flood_until'].strftime('%H:%M:%S') if c['flood_until'] else 'Unknown'}"
        config_status.append(f"Config {c['id']} ({c['name']}): {status} | Requests: {c['request_count']}")
    
    status_html = "<br>".join(config_status)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BRONX ULTRA API - 3 CONFIGS</title>
        <style>
            body {{ background: #000; color: #0ff; font-family: monospace; text-align: center; padding: 50px; }}
            code {{ background: #111; padding: 10px; color: #fa0; border-radius: 5px; display: block; margin: 10px 0; }}
            .status {{ background: #111; padding: 15px; border-radius: 10px; margin: 20px 0; text-align: left; color: #0f0; font-size: 12px; }}
            .btn {{ background: #fa0; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }}
        </style>
    </head>
    <body>
        <h1>🆔 BRONX ULTRA API</h1>
        <h2>⚡ 3 CONFIGURATIONS AUTO-ROTATE</h2>
        
        <div class="status">
            <strong>📊 CONFIG STATUS:</strong><br>
            {status_html}
        </div>
        
        <code>GET /chatid?username=USERNAME</code>
        <code>GET /config-status</code>
        <code>GET /clear-cache</code>
        
        <p style="color:#555; margin-top:30px;">{CREDIT}</p>
        <p style="color:#0f0;">🔥 AUTO-ROTATE | 3 CONFIGS | 24H CACHE</p>
    </body>
    </html>
    """

@app.route('/chatid')
def chatid():
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({
            "status": "error",
            "message": "Missing username",
            "credit": CREDIT
        }), 400
    
    # Check cache first
    cached_result = get_cached_result(username)
    if cached_result:
        cached_result['cache_hit'] = True
        cached_result['credit'] = CREDIT
        return jsonify(cached_result)
    
    # Get active config
    config, error_msg = get_active_config()
    if not config:
        return jsonify({
            "status": "error",
            "message": error_msg,
            "credit": CREDIT
        }), 429
    
    async def get():
        entity = await get_entity_with_config(config, username)
        clean = username.replace("@", "")
        
        result = {
            "status": "success",
            "chat_id": entity.id,
            "username": getattr(entity, 'username', clean),
            "config_used": f"Config {config['id']} ({config['name']})",
            "config_request_count": config['request_count'],
            "credit": CREDIT,
            "by": CREDIT
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
            result["phone"] = getattr(entity, 'phone', None)
        
        return result
    
    try:
        result = loop.run_until_complete(get())
        set_cached_result(username, result)
        result['cache_hit'] = False
        return jsonify(result)
        
    except FloodWaitError as e:
        # Try next config automatically
        config, _ = get_active_config()
        if config:
            try:
                result = loop.run_until_complete(get())
                set_cached_result(username, result)
                result['cache_hit'] = False
                result['auto_rotated'] = True
                return jsonify(result)
            except FloodWaitError as e2:
                return jsonify({
                    "status": "error",
                    "message": f"All configs rate limited. Max wait: {e2.seconds}s",
                    "credit": CREDIT
                }), 429
            except Exception as e2:
                return jsonify({
                    "status": "error",
                    "message": str(e2),
                    "credit": CREDIT
                }), 404
        
        return jsonify({
            "status": "error",
            "message": f"Rate limited: {e.seconds} seconds. Auto-rotating to next config...",
            "credit": CREDIT
        }), 429
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "credit": CREDIT
        }), 404

@app.route('/config-status')
def config_status():
    """View all config statuses"""
    status_list = []
    for c in CONFIGURATIONS:
        status_list.append({
            "config_id": c['id'],
            "name": c['name'],
            "is_active": c['is_active'],
            "flood_until": c['flood_until'].strftime('%Y-%m-%d %H:%M:%S') if c['flood_until'] else None,
            "request_count": c['request_count'],
            "api_id": str(c['api_id'])[:4] + "****"  # Hide full API ID
        })
    
    return jsonify({
        "status": "success",
        "active_config": CONFIGURATIONS[current_config_index]['name'],
        "configs": status_list,
        "credit": CREDIT
    })

@app.route('/clear-cache')
def clear_cache():
    cache.clear()
    return jsonify({
        "status": "success",
        "message": "Cache cleared",
        "credit": CREDIT
    })

@app.route('/cache-stats')
def cache_stats():
    return jsonify({
        "status": "success",
        "cached_usernames": len(cache),
        "cache_ttl_hours": CACHE_TTL // 3600,
        "total_requests": sum([c['request_count'] for c in CONFIGURATIONS]),
        "credit": CREDIT
    })

@app.route('/health')
def health():
    active_configs = sum([1 for c in CONFIGURATIONS if c['is_active']])
    return jsonify({
        "status": "ok",
        "active_configs": active_configs,
        "total_configs": len(CONFIGURATIONS),
        "cached_entries": len(cache),
        "credit": CREDIT
    })

# ============================================
# SWITCH CONFIG (Manual)
# ============================================
@app.route('/switch-config')
def switch_config():
    """Manually switch to next config"""
    global current_config_index
    with config_lock:
        current_config_index = (current_config_index + 1) % 3
    
    return jsonify({
        "status": "success",
        "message": f"Switched to Config {CONFIGURATIONS[current_config_index]['id']} ({CONFIGURATIONS[current_config_index]['name']})",
        "credit": CREDIT
    })

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    # Initialize all configs
    async def init():
        for config in CONFIGURATIONS:
            try:
                client = TelegramClient(
                    StringSession(config['session_string']),
                    config['api_id'],
                    config['api_hash'],
                    loop=loop
                )
                await client.connect()
                if await client.is_user_authorized():
                    config['client'] = client
                    print(f"✅ Config {config['id']} ({config['name']}) - Ready")
                else:
                    print(f"⚠️ Config {config['id']} ({config['name']}) - Not authorized!")
            except Exception as e:
                print(f"❌ Config {config['id']} ({config['name']}) - Error: {e}")
    
    try:
        loop.run_until_complete(init())
    except Exception as e:
        print(f"Init error: {e}")
    
    print(f"""
    ╔══════════════════════════════════╗
    ║   BRONX ULTRA API - 3 CONFIGS   ║
    ║   AUTO-ROTATE ENABLED           ║
    ║   CACHE: 24 HOURS               ║
    ╚══════════════════════════════════╝
    """)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
