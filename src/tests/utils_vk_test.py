# coding: utf-8

import pytest

from services.vk import utils


def test_extractAccessTokenFromFullURL():
	"""
	`extract_access_token_from_url()` извлекает ACCESS_TOKEN из URL.
	"""

	assert utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=123456789") == "123456789"
	assert utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789") == "aaaaaaaaa"
	assert utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789&other_param=123456789") == "aaaaaaaaa"

	with pytest.raises(Exception):
		utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=&expires_in=86400&user_id=123456789&other_param=123456789&another_param=123456789")
		utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#&expires_in=86400&user_id=123456789&other_param=123456789&another_param=123456789")

def test_randomID():
	"""
	`random_id()` генерирует случайный ID для отправки сообщения ВКонтакте.
	"""

	assert isinstance(utils.random_id(), int)

def test_vkLongpollFlagsParser():
	"""
	Класс `VKLongpollMessageFlags` принимает в себя флаги сообщения ВКонтакте и парсит их.
	"""

	flags = utils.VKLongpollMessageFlags(1+8+16+256+65536)
	assert flags.unread
	assert flags.important
	assert flags.chat
	assert flags.fixed
	assert flags.hidden

	flags = utils.VKLongpollMessageFlags(2+64+512+8192)
	assert flags.outbox
	assert flags.spam
	assert flags.delete_for_all
	assert flags.not_delivered
	assert flags.media

def test_createMessageLink():
	"""
	`create_message_link()` создаёт ссылку на сообщение.
	"""

	assert utils.create_message_link(123456789, 321, use_mobile=False) == "https://vk.com/im?sel=123456789&msgid=321"
	assert isinstance(utils.create_message_link(123456789, 321, use_mobile=False), str)

	assert utils.create_message_link(123456789, 321, use_mobile=True) == "https://m.vk.com/mail?act=msg&id=321"
	with pytest.raises(Exception):
		utils.create_message_link(None, 321, use_mobile=False)

def test_createDialogueLink():
	"""
	`create_dialogue_link()` создаёт ссылку на диалог.
	"""

	assert utils.create_dialogue_link(123456789, use_mobile=False) == "https://vk.com/im?sel=123456789"
	assert isinstance(utils.create_dialogue_link(123456789, use_mobile=False), str)

	assert utils.create_dialogue_link(123456789, use_mobile=True) == "https://m.vk.com/mail?act=show&chat=123456789"

def test_getAttachmentKey():
	"""
	`get_attachment_key()` создаёт строку с вложением ВКонтакте.
	"""

	assert utils.get_attachment_key({"owner_id": 123, "id": 456}, type="photo") == "photo123_456"
	assert utils.get_attachment_key({"owner_id": 123, "id": 456}, type="video") == "video123_456"
	assert utils.get_attachment_key({"owner_id": 123, "id": 456}) == "123_456"
	assert utils.get_attachment_key({"owner_id": 123, "video_id": 456}, type="video") == "video123_456"
	assert utils.get_attachment_key({"owner_id": 123, "video_id": 456, "access_key": "secret"}, type="video") == "video123_456_secret"
	assert utils.get_attachment_key({"owner_id": 123, "video_id": 456, "access_key": "secret"}, type="video", include_access_key=False) == "video123_456"

def test_getMessageMentions():
	"""
	`get_message_mentions()` извлекает и возвращает список из упоминаний в тексте сообщения.
	"""

	assert utils.get_message_mentions("Привет, [@durov|id1] и [@club1|club1]! [нет] [@тест]") == [("@durov", "id1"), ("@club1", "club1")]
	assert utils.get_message_mentions("тест") == []

def test_extractIDFromDomain():
	"""
	`extract_id_from_domain()` извлекает из строки вида `id1` или `club1` цифровой ID.
	"""

	assert utils.extract_id_from_domain("id1") == 1
	assert utils.extract_id_from_domain("club1") == -1

	with pytest.raises(AssertionError):
		utils.extract_id_from_domain("aaa")
