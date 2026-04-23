import httpx
import yt_dlp
import uvicorn
import asyncio
import random
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from cachetools import TTLCache
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

# Data saving middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Thread pool for yt-dlp (Blocking tasks ko handle karne ke liye)
executor = ThreadPoolExecutor(max_workers=10)

# ================== CONFIGURATION ==================
TARGET_SITE = "https://shrutibots.site"
TELEGRAM_BOT_TOKEN = "8624467193:AAHxAsD7fmgUxjNOhyq2h6SeVLBEvOnHadU" 
TELEGRAM_CHAT_ID = "-1003825322575"     
# ===================================================

search_cache = TTLCache(maxsize=300, ttl=7200)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
]

client = httpx.AsyncClient(
    follow_redirects=True, 
    http2=True, 
    timeout=httpx.Timeout(40.0, connect=15.0),
    limits=httpx.Limits(max_connections=200, max_keepalive_connections=50)
)

async def log_event(msg: str):
    try:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
        )
    except: pass

async def track(request: Request, type: str, q: str = None):
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0]
    ua = request.headers.get("user-agent", "Unknown")[:50]
    m = f"🔔 <b>{type}</b>\nIP: <code>{ip}</code>\nDevice: <code>{ua}</code>"
    if q: m += f"\nSearch: <b>{q}</b>"
    asyncio.create_task(log_event(m))

# --- YT-DLP CORE ENGINE (FIXED) ---
def search_youtube(query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'source_address': '0.0.0.0', 
        'default_search': 'ytsearch8', # 8 results mangao
        'user_agent': random.choice(USER_AGENTS),
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch8:{query}", download=False)
            if not info or 'entries' not in info:
                return []
            
            results = []
            for entry in info['entries']:
                if entry:
                    results.append({
                        "title": entry.get('title', 'No Title'),
                        "url": f"https://www.youtube.com/watch?v={entry.get('id')}"
                    })
            return results
    except Exception as e:
        print(f"Scraping Error: {e}")
        return []

@app.get("/api/search")
async def api_search(q: str, request: Request):
    if not q or len(q) < 2:
        return {"results": []}
        
    await track(request, "Music Search", q)
    
    if q in search_cache:
        return {"results": search_cache[q]}
    
    # Run yt-dlp in a separate thread pool so it doesn't block FastAPI
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(executor, search_youtube, q)
        if results:
            search_cache[q] = results
        return {"results": results}
    except Exception as e:
        return JSONResponse(content={"results": [], "error": str(e)}, status_code=500)

# --- MOBILE RESPONSIVE UI ---
KIRU_UI = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    #k-box {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.85); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
        z-index: 99999; display: none; align-items: center; justify-content: center; font-family: 'Inter', sans-serif;
    }
    .k-card {
        width: 90%; max-width: 380px; background: #1a1a1a;
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 30px;
        padding: 25px; color: white; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }
    .k-bar { display: flex; gap: 6px; justify-content: center; margin-bottom: 20px; }
    .k-dot { width: 25px; height: 3px; background: rgba(255,255,255,0.1); border-radius: 10px; }
    .k-dot.active { background: #22c55e; }
    .k-title { font-size: 20px; font-weight: 600; margin: 0 0 8px 0; }
    .k-input { width: 100%; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); border-radius: 15px; padding: 14px; color: white; margin-bottom: 15px; outline: none; font-size: 16px; box-sizing: border-box; }
    .k-input:focus { border-color: #22c55e; }
    .k-item { background: rgba(255,255,255,0.05); border-radius: 15px; padding: 12px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; transition: 0.3s; }
    .k-item:active { background: rgba(34, 197, 94, 0.2); }
    .k-float { position: fixed; bottom: 30px; right: 25px; width: 60px; height: 60px; background: #22c55e; color: black; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 99998; font-size: 24px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
    #kRes { max-height: 250px; overflow-y: auto; scrollbar-width: none; }
</style>

<div class="k-float" onclick="document.getElementById('k-box').style.display='flex'">🎵</div>

<div id="k-box">
    <div class="k-card">
        <div class="k-bar"><div class="k-dot active"></div><div class="k-dot"></div><div class="k-dot"></div></div>
        <h2 class="k-title">Mobile Music</h2>
        <input type="text" id="kQuery" class="k-input" placeholder="Enter song name..." onkeypress="if(event.key==='Enter') doSearch()">
        <div id="kRes"></div>
        <div style="margin-top:20px; font-size:14px; color:#22c55e; cursor:pointer;" onclick="document.getElementById('k-box').style.display='none'">Dismiss</div>
    </div>
</div>

<script>
async function doSearch() {
    const q = document.getElementById('kQuery').value;
    const res = document.getElementById('kRes');
    if(!q) return;
    res.innerHTML = "<p style='color:#22c55e;'>Searching YouTube...</p>";
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await response.json();
        res.innerHTML = "";
        if(!data.results || data.results.length === 0) {
            res.innerHTML = "<p>No results. Try another name.</p>";
            return;
        }
        data.results.forEach(s => {
            res.innerHTML += `<div class="k-item" onclick="window.open('${s.url}', '_blank')">
                <span style="font-size:13px; text-align:left; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; width:80%;">${s.title}</span>
                <span style="color:#22c55e;">▶</span>
            </div>`;
        });
    } catch(e) { res.innerHTML = "Network Error."; }
}
</script>
"""

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    # API calls ko proxy nahi karna hai
    if path.startswith("api/"):
        return JSONResponse({"error": "Invalid API path"}, status_code=404)

    asyncio.create_task(track(request, "Site Visit"))

    url = f"{TARGET_SITE}/{path}"
    headers = dict(request.headers)
    # Important: Host header target site ka hona chahiye
    headers["host"] = "shrutibots.site"
    headers["user-agent"] = random.choice(USER_AGENTS)

    try:
        content_body = await request.body()
        resp = await client.request(
            request.method, 
            url, 
            headers=headers, 
            params=request.query_params, 
            content=content_body
        )
        
        # HTML content mein UI inject karein
        if "text/html" in resp.headers.get("content-type", "").lower():
            text = resp.text.replace(TARGET_SITE, "")
            if "</body>" in text:
                text = text.replace("</body>", f"{KIRU_UI}</body>")
            else:
                text += KIRU_UI
            return HTMLResponse(text, status_code=resp.status_code)
            
        return Response(content=resp.content, headers=dict(resp.headers), status_code=resp.status_code)
    except Exception as e:
        return HTMLResponse(f"Server Error: {str(e)}", status_code=502)

if __name__ == "__main__":
    # Port 8000 default hai, ise aap change kar sakte hain
    uvicorn.run(app, host="0.0.0.0", port=8000)
