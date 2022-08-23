# coding: utf-8

from .Base import baseTelehooperAPI

class VKTelehooperAPI(baseTelehooperAPI):
	"""
	API для работы над ВКонтакте.
	"""

	def __init__(self) -> None:
		super().__init__()

		available = True
		serviceCodename = "vk"
		serviceName = "ВКонтакте"
