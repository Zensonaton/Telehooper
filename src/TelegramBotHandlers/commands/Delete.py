# coding: utf-8

"""Обработчик для команды `Delete`."""

from typing import cast
from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from ServiceAPIs.VK import VKTelehooperAPI
from TelegramBot import Telehooper

TELEHOOPER: Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(Delete, commands=["delete", "del", "remove"])


async def Delete(msg: MessageType) -> None:
	TELEHOOPER.vkAPI = cast(VKTelehooperAPI, TELEHOOPER.vkAPI)

	# Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(msg.from_user.id)

	# Проверяем, подключён ли у него ВК:
	if not user.isVKConnected:
		return

	# Проверяем, есть ли reply:
	if not msg.reply_to_message:
		await msg.reply(f"Для использования команды <code>{msg.get_command()}</code> сделай ответ на сообщение, что бы его удалить.")

		return


	# Узнаём, диалог ли это:
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)
	if not dialogue:
		return

	# ID сообщения:
	selMessage = TELEHOOPER.vkAPI.getMessageDataByTelegramMID(
		user,
		msg.reply_to_message.message_id
	)
	if not selMessage:
		return

	# Удаляем сообщение для всех:
	await TELEHOOPER.vkAPI.deleteMessage(
		user,
		selMessage.serviceDialogueID,
		selMessage.serviceMID,
		True
	)

