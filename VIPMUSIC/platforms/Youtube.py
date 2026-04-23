import asyncio
import re
import aiohttp
from typing import Union, Tuple
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch, Playlist
from ShrutiMusic.utils.formatters import time_to_seconds
from ShrutiMusic import LOGGER

# External API Configuration
API_URL = "https://kiru-bot.up.railway.app"

async def get_direct_stream_link(link: str, m_type: str = "audio") -> str:
    """
    Fetches the direct streaming URL from the external API.
    This method is secure as it doesn't store files locally.
    """
    # Security: Extract and sanitize Video ID to prevent malicious input
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)

    if not video_id or len(video_id) < 3:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Request the download token from the API
            params = {"url": video_id, "type": m_type}
            async with session.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                download_token = data.get("download_token")

                if not download_token:
                    return None

                # Step 2: Construct the final direct stream URL
                # This URL can be passed directly to the music player
                stream_url = f"{API_URL}/stream/{video_id}?type={m_type}&token={download_token}"
                return stream_url

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
        for result in (await results.next())["result"]:
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
        for result in (await results.next())["result"]:
            return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """Returns the direct stream URL for a video"""
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
            plist = await Playlist.get(link)
            videos = plist.get("videos") or []
            return [data.get("id") for data in videos[:limit] if data.get("id")]
        except Exception:
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
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

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
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
        """
        Instead of downloading to a file, this returns the direct API stream URL.
        Safe for server health and efficient for streaming.
        """
        if videoid:
            link = self.base + link

        m_type = "video" if video else "audio"
        stream_link = await get_direct_stream_link(link, m_type=m_type)

        if stream_link:
            return stream_link, True
        return None, False
