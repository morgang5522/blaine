import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from telegram.ext import ApplicationHandlerStop

import src.bot as bot


def _update(user_id):
    user = None if user_id is None else SimpleNamespace(id=user_id, username="someone")
    return SimpleNamespace(effective_user=user)


class TestAllowedUsers(unittest.TestCase):
    def test_is_user_allowed(self):
        self.assertTrue(bot.is_user_allowed(1, [1, 2]))
        self.assertFalse(bot.is_user_allowed(3, [1, 2]))

    def test_empty_whitelist_denies_everyone(self):
        self.assertFalse(bot.is_user_allowed(1, []))

    def test_guard_passes_allowed_user(self):
        with patch.object(bot.settings, "TELEGRAM_ALLOWED_USERS", [42]):
            asyncio.run(bot.enforce_allowed_users(_update(42), None))

    def test_guard_stops_unknown_user(self):
        with patch.object(bot.settings, "TELEGRAM_ALLOWED_USERS", [42]):
            with self.assertRaises(ApplicationHandlerStop):
                asyncio.run(bot.enforce_allowed_users(_update(7), None))

    def test_guard_stops_update_without_user(self):
        with patch.object(bot.settings, "TELEGRAM_ALLOWED_USERS", [42]):
            with self.assertRaises(ApplicationHandlerStop):
                asyncio.run(bot.enforce_allowed_users(_update(None), None))


if __name__ == "__main__":
    unittest.main()
