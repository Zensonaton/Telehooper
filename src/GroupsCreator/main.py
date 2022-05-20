# coding: utf-8

from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import EditChatAdminRequest
import telethon
import dotenv
import os

# Грузим .env файл:
dotenv.load_dotenv()

if not os.environ["RECIEVER"].lower().endswith("bot"):
	raise Exception("RECIEVER не является ботом.")


async def job(client: telethon.TelegramClient) -> None:
	chatid = (await client(CreateChannelRequest("ㅤ", "", megagroup=True))).chats[0].id # type: ignore
	await client(InviteToChannelRequest(chatid, [os.environ["RECIEVER"]])) # type: ignore
	await client.edit_admin(
		chatid,
		os.environ["RECIEVER"],
		
		change_info = True, 
		post_messages = True, 
		edit_messages = True, 
		delete_messages = True, 
		ban_users = True, 
		invite_users = True, 
		pin_messages = True, 
		add_admins = True, 
		manage_call = True, 
		anonymous = False, 
		is_admin = True
	)



with telethon.TelegramClient("user", int(os.environ["API_ID"]), os.environ["API_HASH"]) as client:
	client.loop.run_until_complete(job(client))


