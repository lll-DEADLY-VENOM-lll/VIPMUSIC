import asyncio
import os
import re
import logging
import aiohttp
import yt_dlp
from typing import Union, Optional, Tuple, List
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from VIPMUSIC.utils.formatters import time_to_seconds
from VIPMUSIC import LOGGER

# --- CONFIGURATION & SECURITY ---
try:
    from config import API_ID, BOT_TOKEN, MONGO_DB_URI
except ImportError:
    LOGGER.error("Config file not found!")

class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.msg)
        patterns = [r"\d{8,10}:[a-zA-Z0-9_-]{35,}", r"mongodb\+srv://\S+"]
        for pattern in patterns:
            msg = re.sub(pattern, "[PROTECTED]", msg)
        record.msg = msg
        return True

logging.getLogger().addFilter(SensitiveDataFilter())

API_URL = "http://kiru-bot.up.railway.app"

# --- JBL SOUND EFFECT ARGUMENTS ---
# Iska use audio stream karte waqt FFmpeg mein hota hai.
# Bass ko 10dB boost kiya gaya hai aur treble ko crystal clear banaya gaya hai.
JBL_FFMPEG_ARGS = "-af \"bass=g=10,treble=g=3,equalizer=f=40:width_type=h:width=50:g=10\""

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "source_address": "0.0.0.0",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
        }

    async def exists(self, link: str):
        """Check if link is a valid YouTube URL"""
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Optional[str]:
        """Extracts URL from message/reply with high accuracy"""
        messages = [message, message.reply_to_message]
        for msg in messages:
            if not msg: continue
            text = msg.text or msg.caption
            if not text: continue

            if msg.entities:
                for entity in msg.entities:
                    if entity.type == MessageEntityType.URL:
                        return text[entity.offset : entity.offset + entity.length]
            
            urls = re.findall(r'(https?://\S+)', text)
            if urls: return urls[0]
        return None

    async def search(self, query: str, limit: int = 1):
        """Smart Search: First tries API, then fallback to yt-dlp"""
        try:
            # Primary Search
            search = VideosSearch(query, limit=limit)
            resp = await search.next()
            if resp.get("result"):
                return resp.get("result")
            
            # Fallback Search (Agar primary fail ho jaye)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(self.ydl_opts).extract_info(f"ytsearch{limit}:{query}", download=False)
            )
            if 'entries' in info:
                return [{
                    "title": x["title"],
                    "duration": x.get("duration_string", "05:00"),
                    "thumbnails": [{"url": x["thumbnail"]}],
                    "id": x["id"],
                    "link": f"https://www.youtube.com/watch?v={x['id']}"
                } for x in info['entries']]
        except Exception as e:
            LOGGER.error(f"Search Error: {e}")
        return []

    async def details(self, query: str, videoid: Union[bool, str] = None):
        """Fetches video details with error handling"""
        try:
            if videoid or await self.exists(query):
                link = self.base + query if videoid else query.split("&")[0]
                results = VideosSearch(link, limit=1)
                res_data = await results.next()
                res = res_data.get("result", [])
            else:
                res = await self.search(query, limit=1)

            if not res: return None
            video = res[0]
            
            title = video.get("title", "Unknown Title")
            duration = video.get("duration", "05:00")
            if not duration or duration == "None": duration = "05:00"
            
            return (
                title,
                duration,
                int(time_to_seconds(duration)),
                video["thumbnails"][0]["url"].split("?")[0],
                video["id"]
            )
        except Exception as e:
            LOGGER.error(f"Details Error: {e}")
            return None

    async def track(self, query: str, videoid: Union[bool, str] = None):
        """Main track extractor for the music player"""
        det = await self.details(query, videoid)
        if not det: return None, None
        track_details = {
            "title": det[0],
            "link": self.base + det[4],
            "vidid": det[4],
            "duration_min": det[1],
            "thumb": det[3],
        }
        return track_details, det[4]

    async def download(
        self,
        link: str,
        mystic=None,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        **kwargs
    ) -> Tuple[Optional[str], bool]:
        """Downloads/Extracts streamable URL with JBL sound compatibility"""
        if videoid: link = self.base + link
        m_type = "video" if video else "audio"
        
        # 1. High Speed API Try
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{API_URL}/download", params={"url": link, "type": m_type}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        token = data.get("download_token")
                        if token:
                            return f"{API_URL}/stream/{link}?type={m_type}&token={token}", True
        except:
            pass
        
        # 2. Reliable Fallback (yt-dlp) - solve GroupcallInvalid issues
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, link, download=False)
                if 'url' in info:
                    return info['url'], True
        except Exception as e:
            LOGGER.error(f"Download Error: {e}")
            
        return None, False

# Initialize
YouTube = YouTubeAPI()
