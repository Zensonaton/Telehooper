# coding: utf-8

"""Handler для команды `ConvertToServiceDialogue`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `ConvertToServiceDialogue`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(ConvertToServiceDialogue, commands=["converttoservicedialogue"])


async def ConvertToServiceDialogue(msg: MessageType):
	await msg.reply("")
