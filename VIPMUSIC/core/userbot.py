#
# Copyright (C) 2024 by THE-VIP-BOY-OP@Github, < https://github.com/THE-VIP-BOY-OP >.
#
# This file is part of < https://github.com/THE-VIP-BOY-OP/VIP-MUSIC > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/THE-VIP-BOY-OP/VIP-MUSIC/blob/master/LICENSE >
#
# All rights reserved.
#

from typing import Callable, Optional
import pyrogram
from pyrogram import Client
import config
from ..logging import LOGGER

assistants = []
assistantids = []
clients = []

class Userbot(Client):
    def __init__(self):
        self.one = Client("VIPString1", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING1))
        self.two = Client("VIPString2", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING2))
        self.three = Client("VIPString3", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING3))
        self.four = Client("VIPString4", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING4))
        self.five = Client("VIPString5", api_id=config.API_ID, api_hash=config.API_HASH, session_string=str(config.STRING5))

    async def start(self):
        LOGGER(__name__).info(f"Starting Assistant Clients...")
        
        # Assistant configurations ka data ek list mein
        as_data = [
            (self.one, config.STRING1, 1),
            (self.two, config.STRING2, 2),
            (self.three, config.STRING3, 3),
            (self.four, config.STRING4, 4),
            (self.five, config.STRING5, 5),
        ]
        
        # Jin channels ko join karna hai
        CHATS = ["about_deadly_venom", "ll_DEADLY_VENOM_ll", "NOBITA_SUPPORT", "https://t.me/+5YDHR8Ep5AdlNTI9"]

        for client, string, count in as_data:
            if string:
                await client.start()
                # Join logic ko ek line mein handle kiya
                for chat in CHATS:
                    try:
                        await client.join_chat(chat)
                    except:
                        pass
                
                assistants.append(count)
                clients.append(client)
                
                try:
                    await client.send_message(config.LOG_GROUP_ID, f"Assistant {count} Started")
                except:
                    LOGGER(__name__).error(f"Assistant Account {count} failed to access Log Group. Add and promote it!")

                get_me = await client.get_me()
                client.username = get_me.username
                client.id = get_me.id
                client.mention = get_me.mention
                client.name = f"{get_me.first_name} {get_me.last_name or ''}".strip()
                assistantids.append(get_me.id)
                LOGGER(__name__).info(f"Assistant {count} Started as {client.name}")

def on_cmd(filters: Optional[pyrogram.filters.Filter] = None, group: int = 0) -> Callable:
    def decorator(func: Callable) -> Callable:
        for client in clients:
            client.add_handler(pyrogram.handlers.MessageHandler(func, filters), group)
        return func
    return decorator
