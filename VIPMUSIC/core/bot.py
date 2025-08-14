# Copyright (C) 2024 by VISHAL-PANDEY@Github, <https://github.com/vishalpandeynkp1>
#
# This file is part of <https://github.com/vishalpandeynkp1/VIPNOBITAMUSIC_REPO> project,
# and is released under the "GNU v3.0 License Agreement".
# Please see <https://github.com/vishalpandeynkp1/VIPNOBITAMUSIC_REPO/blob/master/LICENSE>
#
# All rights reserved.

import uvloop
uvloop.install()

import pyrogram
import pyromod.listen  # noqa
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

import config
from ..logging import LOGGER


class VIPBot(Client):
    def __init__(self):
        LOGGER(__name__).info("Starting Bot...")
        super().__init__(
            "VIPMUSIC",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
        )

    async def start(self):
        await super().start()
        get_me = await self.get_me()
        self.username = get_me.username
        self.id = get_me.id
        self.name = get_me.first_name + (" " + get_me.last_name if get_me.last_name else "")
        self.mention = get_me.mention

        # Create the add to group button
        button = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="๏ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ ๏",
                        url=f"https://t.me/{self.username}?startgroup=true",
                    )
                ]
            ]
        )

        # Send startup message to log group if configured
        await self._send_startup_message(button)
        
        # Set bot commands if enabled in config
        if config.SET_CMDS:
            await self._setup_bot_commands()
        
        # Verify bot admin status in log group
        await self._verify_bot_admin_status()
        
        LOGGER(__name__).info(f"MusicBot Started Successfully as {self.name}")

    async def _send_startup_message(self, button):
        if not config.LOG_GROUP_ID:
            LOGGER(__name__).warning("LOG_GROUP_ID not set, skipping startup notification")
            return

        caption = (
            "╔════❰𝐖𝐄𝐋𝐂𝐎𝐌𝐄❱════❍⊱❁۪۪\n"
            "║\n"
            f"║┣⪼🥀𝐁𝐨𝐭 𝐒𝐭𝐚𝐫𝐭𝐞𝐝 𝐁𝐚𝐛𝐲🎉\n"
            "║\n"
            f"║┣⪼ {self.name}\n"
            "║\n"
            f"║┣⪼🎈𝐈𝐃:- `{self.id}` \n"
            "║\n"
            f"║┣⪼🎄@{self.username} \n"
            "║ \n"
            "║┣⪼💖𝐓𝐡𝐚𝐧𝐤𝐬 𝐅𝐨𝐫 𝐔𝐬𝐢𝐧𝐠😍\n"
            "║\n"
            "╚════════════════❍⊱❁"
        )

        try:
            if config.START_IMG_URL:
                await self.send_photo(
                    config.LOG_GROUP_ID,
                    photo=config.START_IMG_URL,
                    caption=caption,
                    reply_markup=button,
                )
            else:
                await self.send_message(
                    config.LOG_GROUP_ID,
                    text=caption,
                    reply_markup=button,
                )
        except pyrogram.errors.ChatWriteForbidden:
            LOGGER(__name__).error("Bot doesn't have permission to write in log group")
        except Exception as e:
            LOGGER(__name__).error(f"Failed to send startup message: {e}")

    async def _setup_bot_commands(self):
        try:
            # Private chat commands
            await self.set_bot_commands(
                commands=[
                    BotCommand("start", "Start the bot"),
                    BotCommand("help", "Get the help menu"),
                    BotCommand("ping", "Check if the bot is alive"),
                ],
                scope=BotCommandScopeAllPrivateChats(),
            )

            # Group chat commands
            await self.set_bot_commands(
                commands=[
                    BotCommand("play", "Start playing requested song"),
                    BotCommand("stop", "Stop the current song"),
                    BotCommand("pause", "Pause the current song"),
                    BotCommand("resume", "Resume the paused song"),
                    BotCommand("queue", "Check the queue of songs"),
                    BotCommand("skip", "Skip the current song"),
                    BotCommand("volume", "Adjust the music volume"),
                    BotCommand("lyrics", "Get lyrics of the song"),
                ],
                scope=BotCommandScopeAllGroupChats(),
            )

            # Admin commands
            await self.set_bot_commands(
                commands=[
                    BotCommand("start", "❥ Start the bot"),
                    BotCommand("ping", "❥ Check the ping"),
                    BotCommand("help", "❥ Get help"),
                    BotCommand("vctag", "❥ Tag all for voice chat"),
                    BotCommand("stopvctag", "❥ Stop tagging for VC"),
                    BotCommand("tagall", "❥ Tag all members by text"),
                    BotCommand("cancel", "❥ Cancel the tagging"),
                    BotCommand("settings", "❥ Get the settings"),
                    BotCommand("reload", "❥ Reload the bot"),
                    BotCommand("play", "❥ Play the requested song"),
                    BotCommand("vplay", "❥ Play video along with music"),
                    BotCommand("end", "❥ Empty the queue"),
                    BotCommand("playlist", "❥ Get the playlist"),
                    BotCommand("stop", "❥ Stop the song"),
                    BotCommand("lyrics", "❥ Get the song lyrics"),
                    BotCommand("song", "❥ Download the requested song"),
                    BotCommand("video", "❥ Download the requested video song"),
                    BotCommand("gali", "❥ Reply with fun"),
                    BotCommand("shayri", "❥ Get a shayari"),
                    BotCommand("love", "❥ Get a love shayari"),
                    BotCommand("sudolist", "❥ Check the sudo list"),
                    BotCommand("owner", "❥ Check the owner"),
                    BotCommand("update", "❥ Update bot"),
                    BotCommand("gstats", "❥ Get stats of the bot"),
                    BotCommand("repo", "❥ Check the repo"),
                ],
                scope=BotCommandScopeAllChatAdministrators(),
            )
        except Exception as e:
            LOGGER(__name__).error(f"Failed to set bot commands: {e}")

    async def _verify_bot_admin_status(self):
        if not config.LOG_GROUP_ID:
            return

        try:
            chat_member = await self.get_chat_member(config.LOG_GROUP_ID, self.id)
            if chat_member.status != ChatMemberStatus.ADMINISTRATOR:
                LOGGER(__name__).error("Please promote bot as Admin in Logger Group")
        except Exception as e:
            LOGGER(__name__).error(f"Error checking bot admin status: {e}")
