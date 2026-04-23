import asyncio
import re
import aiohttp
from typing import Union, Tuple
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch, Playlist
from VIPMUSIC.utils.formatters import time_to_seconds
from VIPMUSIC import LOGGER

# External API Configuration
API_URL = "https://kiru-bot.up.railway.app"

async def get_direct_stream_link(link: str, m_type: str = "audio") -> str:
    """
    Fetches the direct streaming URL from the external API.
    """
    # Better Regex to extract Video ID
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
    video_id = video_id_match.group(1) if video_id_match else link
    
    video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)

    if not video_id or len(video_id) < 11:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": m_type}
            async with session.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                download_token = data.get("download_token")

                if not download_token:
                    return None

                return f"{API_URL}/stream/{video_id}?type={m_type}&token={download_token}"

    except Exception as e:
        LOGGER(__name__).error(f"Streaming link generation error: {e}")
        return None


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset: entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        results = VideosSearch(link, limit=1)
        search_res = (await results.next())["result"]
        
        if not search_res:
            return None, None, None, None, None
            
        result = search_res[0]
        title = result["title"]
        duration_min = result["duration"]
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]
        duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        res = (await results.next())["result"]
        return res[0]["title"] if res else None

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        res = (await results.next())["result"]
        return res[0]["duration"] if res else None

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        res = (await results.next())["result"]
        return res[0]["thumbnails"][0]["url"].split("?")[0] if res else None

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        stream_url = await get_direct_stream_link(link, m_type="video")
        if stream_url:
            return 1, stream_url
        return 0, "Failed to get video stream link."

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            # Corrected Playlist call for __future__
            plist = Playlist(link)
            videos = (await plist.next())["result"]
            return [data.get("id") for data in videos[:limit] if data.get("id")]
        except Exception as e:
            LOGGER(__name__).error(f"Playlist error: {e}")
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        res = (await results.next())["result"]
        if not res:
            return None, None
            
        result = res[0]
        track_details = {
            "title": result["title"],
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result["duration"],
            "thumb": result["thumbnails"][0]["url"].split("?")[0],
        }
        return track_details, result["id"]

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        ytdl_opts = {"quiet": True}
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                formats_available = []
                r = ydl.extract_info(link, download=False)
                for f in r["formats"]:
                    if "dash" not in str(f["format"]).lower():
                        formats_available.append({
                            "format": f["format"],
                            "filesize": f.get("filesize"),
                            "format_id": f["format_id"],
                            "ext": f["ext"],
                            "format_note": f.get("format_note"),
                            "yturl": link,
                        })
                return formats_available, link
        except Exception:
            return None, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        if not result or len(result) <= query_type:
            return None, None, None, None
        res = result[query_type]
        return res["title"], res["duration"], res["thumbnails"][0]["url"].split("?")[0], res["id"]

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        **kwargs
    ) -> Tuple[str, bool]:
        if videoid:
            link = self.base + link

        m_type = "video" if video else "audio"
        try:
            stream_link = await get_direct_stream_link(link, m_type=m_type)
            if stream_link:
                return stream_link, True
        except Exception as e:
            LOGGER(__name__).error(f"Download link error: {e}")
            
        return None, False
