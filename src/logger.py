# coding: utf-8

import sys

from loguru import logger


def init_logger(debug: bool = False) -> None:
	"""
	Инициализирует логгер.
	"""

	logger.remove()

	logger.add(
		"logs/bot.log",
		rotation="1 week",
		retention="1 month",
		level="DEBUG" if debug else "INFO",
		backtrace=True,
		diagnose=True
	)
	logger.add(sys.stderr, level="DEBUG" if debug else "INFO", diagnose=True)

