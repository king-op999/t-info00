from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime, timedelta

app = Flask(__name__)
CREDIT = "@BRONX_ULTRA"

# ============================================
# 3 API ENDPOINTS (Fallback System)
# ============================================
API_ENDPOINTS = [
    {
        "id": 1,
        "name": "Primary",
        "url": "https://zero02-tg000.onrender.com/chatid",
        "timeout": 10,
        "fail_count": 0,
        "last_fail": None
    },
    {
        "id": 2,
        "name": "Secondary",
        "url": "https://test-ha-opop.onrender.com/chatid",
        "timeout": 10,
        "fail_count": 0,
        "last_fail": None
    },
    {
        "id": 3,
        "name": "Backup",
        "url": "https://tg-tedt-op01.onrender.com/chatid",
        "timeout": 10,
        "fail_count": 0,
        "last_fail": None
    }
]

# Cache for fast responses
cache = {}
CACHE_TTL = 86400  # 24 hours


# ============================================
# CACHE FUNCTIONS
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
# FETCH FROM SINGLE API
# ============================================
def fetch_from_api(api_config, username):
    """Try to fetch from one API"""
    try:
        clean_username = username.replace("@", "").strip()
        url = f"{api_config['url']}?username={clean_username}"
        
        start = time.time()
        response = requests.get(url, timeout=api_config['timeout'])
        elapsed = round((time.time() - start) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if response has error
            if data.get('status') == 'error':
                raise Exception(data.get('message', 'API returned error'))
            
            # Success! Reset fail count
            api_config['fail_count'] = 0
            api_config['last_fail'] = None
            
            # Add our credit and API info
            data['credit'] = CREDIT
            data['by'] = CREDIT
            data['api_used'] = api_config['name']
            data['response_time_ms'] = elapsed
            return data
        
        elif response.status_code == 429:
            raise Exception("Rate limited")
        else:
            raise Exception(f"HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        api_config['fail_count'] += 1
        api_config['last_fail'] = datetime.now()
        raise Exception(f"{api_config['name']} timeout")
    
    except requests.exceptions.ConnectionError:
        api_config['fail_count'] += 1
        api_config['last_fail'] = datetime.now()
        raise Exception(f"{api_config['name']} connection failed")
    
    except Exception as e:
        api_config['fail_count'] += 1
        api_config['last_fail'] = datetime.now()
        raise e


# ============================================
# FETCH WITH FALLBACK (Sequential - One by One)
# ============================================
def fetch_with_fallback(username):
    """Try APIs one by one until success"""
    errors = []
    
    # Try each API sequentially
    for api in API_ENDPOINTS:
        try:
            result = fetch_from_api(api, username)
            return result
        except Exception as e:
            error_msg = str(e)
            errors.append(f"{api['name']}: {error_msg}")
            # Continue to next API
    
    # All APIs failed
    raise Exception(f"All APIs failed! Errors: {' | '.join(errors)}")


# ============================================
# FLASK ROUTES
# ============================================
@app.route('/')
def home():
    api_status = ""
    for api in API_ENDPOINTS:
        if api['fail_count'] == 0:
            status = "✅ Online"
        elif api['fail_count'] < 3:
            status = f"⚠️ {api['fail_count']} fails"
        else:
            status = f"❌ {api['fail_count']} fails"
        
        if api['last_fail']:
            status += f" (Last fail: {api['last_fail'].strftime('%H:%M')})"
        
        api_status += f"{api['name']}: {status}<br>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BRONX ULTRA API</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: #000; color: #0ff; font-family: monospace; text-align: center; padding: 20px; }}
            .box {{ background: #111; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px; text-align: left; }}
            code {{ background: #000; padding: 10px; color: #fa0; display: block; margin: 10px 0; border-radius: 5px; word-break: break-all; }}
            input {{ width: 80%; padding: 12px; background: #222; border: 1px solid #0ff; color: #fff; border-radius: 5px; margin: 10px 0; }}
            button {{ padding: 12px 30px; background: #0ff; color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
            .green {{ color: #0f0; }}
            .red {{ color: #f00; }}
            .yellow {{ color: #ff0; }}
        </style>
    </head>
    <body>
        <h1>🆔 BRONX ULTRA API</h1>
        <h3>3 APIs FALLBACK SYSTEM</h3>
        
        <div class="box">
            <strong>📊 API Status:</strong><br>
            <span class="green">{api_status}</span>
            <br><br>
            <small style="color:#888;">🔄 Sequential Fallback: API 1 → API 2 → API 3</small>
        </div>
        
        <code>GET /api/chatid?username=USERNAME</code>
        
        <input type="text" id="username" placeholder="Enter username..." autocomplete="off">
        <button onclick="lookup()">🔍 GET CHAT ID</button>
        
        <div class="box" id="result" style="display:none;">
            <pre id="resultData" style="color:#0f0; white-space: pre-wrap; word-break: break-all;"></pre>
        </div>
        
        <p style="color:#555; margin-top:20px;">{CREDIT}</p>
        <p style="color:#0f0;">🔥 FALLBACK SYSTEM | 3 APIs | 24H CACHE</p>
        
        <script>
        async function lookup() {{
            var u = document.getElementById('username').value.trim();
            if (!u) return alert('Enter username!');
            var d = document.getElementById('result');
            var p = document.getElementById('resultData');
            d.style.display = 'block';
            p.style.color = '#ff0';
            p.textContent = '🔍 Trying APIs... Please wait...';
            try {{
                var r = await fetch('/api/chatid?username=' + encodeURIComponent(u));
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


@app.route('/api/chatid')
def chatid():
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({
            "status": "error",
            "message": "Username required!",
            "credit": CREDIT
        }), 400
    
    # Check cache first
    cached = get_cached(username)
    if cached:
        cached['cache_hit'] = True
        cached['credit'] = CREDIT
        cached['by'] = CREDIT
        return jsonify(cached)
    
    try:
        # Try APIs one by one (fallback)
        result = fetch_with_fallback(username)
        
        # Cache the result
        set_cached(username, result)
        result['cache_hit'] = False
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)[:300],
            "credit": CREDIT
        }), 503


@app.route('/api/clear-cache')
def clear_cache():
    cache.clear()
    return jsonify({"status": "success", "message": "Cache cleared", "credit": CREDIT})


@app.route('/api/stats')
def stats():
    api_stats = []
    for api in API_ENDPOINTS:
        api_stats.append({
            "name": api['name'],
            "fails": api['fail_count'],
            "last_fail": api['last_fail'].strftime('%Y-%m-%d %H:%M:%S') if api['last_fail'] else None
        })
    
    return jsonify({
        "status": "success",
        "apis": api_stats,
        "cache_size": len(cache),
        "credit": CREDIT
    })


@app.route('/api/health')
def health():
    working = sum([1 for api in API_ENDPOINTS if api['fail_count'] < 5])
    return jsonify({
        "status": "ok" if working > 0 else "all_down",
        "working_apis": working,
        "total_apis": len(API_ENDPOINTS),
        "credit": CREDIT
    })


# Vercel requires this handler
def handler(event, context):
    return app(event, context)
