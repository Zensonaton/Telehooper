# coding: utf-8

class CommandAllowedOnlyInGroup(ValueError):
	"""
	Вызывается, если команда разрешена только в группах.
	"""

	pass

class CommandAllowedOnlyInPrivateChats(ValueError):
	"""
	Вызывается, если команда была вызвана не в приватном чате Telegram.
	"""

	pass

class CommandAllowedOnlyInBotDialogue(ValueError):
	"""
	Вызывается, если команда была вызвана не в диалоге бота Telehooper.
	"""

	pass
