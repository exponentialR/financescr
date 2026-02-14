import importlib
import os
import unittest
from unittest.mock import MagicMock, patch


class SessionModuleConfigTests(unittest.TestCase):
    def _reload_session_module_with_env(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=True):
            import app.db.session as session_module

            return importlib.reload(session_module)

    def test_database_url_uses_default_when_env_missing(self) -> None:
        session_module = self._reload_session_module_with_env({})
        self.assertEqual(
            session_module.DATABASE_URL,
            "postgresql+psycopg://financescr:financescr@localhost:5432/financescr",
        )

    def test_database_url_uses_env_when_provided(self) -> None:
        session_module = self._reload_session_module_with_env(
            {"DATABASE_URL": "postgresql+psycopg://user:pass@db:5432/custom"}
        )
        self.assertEqual(
            session_module.DATABASE_URL,
            "postgresql+psycopg://user:pass@db:5432/custom",
        )

    def test_get_db_yields_session_and_closes_after_iteration(self) -> None:
        session_module = self._reload_session_module_with_env({})
        fake_session = MagicMock(name="session")

        with patch.object(session_module, "SessionLocal", return_value=fake_session):
            generator = session_module.get_db()
            yielded_session = next(generator)

            self.assertIs(yielded_session, fake_session)

            with self.assertRaises(StopIteration):
                next(generator)

        fake_session.close.assert_called_once()

    def test_get_db_closes_session_when_exception_is_raised(self) -> None:
        session_module = self._reload_session_module_with_env({})
        fake_session = MagicMock(name="session")

        with patch.object(session_module, "SessionLocal", return_value=fake_session):
            generator = session_module.get_db()
            next(generator)

            with self.assertRaises(RuntimeError):
                generator.throw(RuntimeError("boom"))

        fake_session.close.assert_called_once()
