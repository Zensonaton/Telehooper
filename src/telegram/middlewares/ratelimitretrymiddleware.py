# coding: utf-8

import asyncio

from aiogram import BaseMiddleware, Bot
from aiogram.client.session.middlewares.base import NextRequestMiddlewareType
from aiogram.dispatcher.dispatcher import DEFAULT_BACKOFF_CONFIG
from aiogram.exceptions import (RestartingTelegram, TelegramNetworkError,
                                TelegramRetryAfter, TelegramServerError)
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.utils.backoff import Backoff, BackoffConfig
from loguru import logger


class RetryRequestMiddleware(BaseMiddleware):
	"""
	Middleware для бота, который будет пытаться по несколько раз повторять запросы к Telegram API, если они не прошли ввиду rate limit.
	"""

	backoff_config: BackoffConfig

	def __init__(self, backoff_config: BackoffConfig = DEFAULT_BACKOFF_CONFIG) -> None:
		"""
		Инициализирует middleware.
		"""

		self.backoff_config = backoff_config

	async def __call__(self, make_request: NextRequestMiddlewareType[TelegramType], bot: Bot, method: TelegramMethod[TelegramType]) -> Response[TelegramType]:
		"""
		Метод, вызываемый при каждом запросе к Telegram API.
		"""

		backoff = Backoff(config=self.backoff_config)

		while True:
			try:
				return await make_request(bot, method)
			except TelegramRetryAfter as e:
				logger.warning(f"Метод '{type(method).__name__}' не удался из-за rate limit. Спим {e.retry_after}с...")

				backoff.reset()
				await asyncio.sleep(e.retry_after)
			except (TelegramServerError, RestartingTelegram, TelegramNetworkError) as e:
				logger.error(f"Метод '{type(method).__name__}' не удался из-за ошибки {type(e).__name__} - {e}. Спим {backoff.next_delay}с...")

				await backoff.asleep()

