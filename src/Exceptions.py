# coding: utf-8

class CommandAllowedOnlyInGroupException(ValueError):
	"""
	Вызывается, если команда разрешена только в группах.
	"""

	pass

class CommandAllowedOnlyInPrivateChatsException(ValueError):
	"""
	Вызывается, если команда была вызвана не в приватном чате Telegram.
	"""

	pass

class CommandAllowedOnlyInBotDialogueException(ValueError):
	"""
	Вызывается, если команда была вызвана не в диалоге бота Telehooper.
	"""

	pass

class CommandRequiresConnectedServiceException(ValueError):
	"""
	Вызывается, если команда была вызвана, когда не был подключён ни один из сервисов.
	"""

	pass

class DisallowedInDebugException(ValueError):
	"""
	Вызывается, если команда была вызвана в debug-режиме, а пользователь не имеет права на использование команд в debug-режиме.
	"""

	pass
