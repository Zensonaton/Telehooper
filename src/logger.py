# coding: utf-8

import sys

from loguru import logger


def init_logger(debug: bool = False) -> None:
	"""
	Инициализирует логгер.

	:param debug: Включает режим отладки.
	"""

	logger.remove()

	logger.add(
		"logs/bot.log",
		rotation="5 MB",
		retention="1 month",
		level="DEBUG" if debug else "INFO",
		backtrace=True,
		diagnose=True
	)
	logger.add(sys.stderr, level="DEBUG" if debug else "INFO", diagnose=True)

