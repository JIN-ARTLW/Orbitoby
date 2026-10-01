from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values

CredentialSource = Literal[
    "runtime",
    "keyring",
    "environment",
    "colab",
    "dotenv",
]


@dataclass(frozen=True, slots=True)
class CredentialResult:
    value: str
    source: CredentialSource


class CredentialManager:
    """Resolve user-owned credentials without exposing secret values.

    Resolution order:
    explicit runtime
    → OS keyring
    → environment
    → Colab Secrets
    → explicit development .env fallback
    """

    def __init__(
        self,
        *,
        runtime: dict[tuple[str, str], str] | None = None,
        allow_dotenv: bool = False,
        dotenv_path: str | Path | None = None,
    ) -> None:
        self._runtime = dict(runtime or {})
        self.allow_dotenv = allow_dotenv

        if dotenv_path is None:
            dotenv_path = Path(__file__).resolve().parents[2] / ".env"

        self.dotenv_path = Path(dotenv_path)

    @staticmethod
    def _normalize(
        provider: str,
        key: str,
    ) -> tuple[str, str]:
        provider = provider.strip().lower()
        key = key.strip().lower()

        if not provider or not key:
            raise ValueError("provider and key must be non-empty")

        return provider, key

    @staticmethod
    def env_name(
        provider: str,
        key: str,
    ) -> str:
        provider, key = CredentialManager._normalize(
            provider,
            key,
        )

        return f"{provider}_{key}".replace("-", "_").upper()

    def set_runtime(
        self,
        provider: str,
        key: str,
        value: str,
    ) -> None:
        provider, key = self._normalize(
            provider,
            key,
        )

        if not value:
            raise ValueError("credential value must not be empty")

        self._runtime[(provider, key)] = value

    def clear_runtime(
        self,
        provider: str,
        key: str,
    ) -> None:
        provider, key = self._normalize(
            provider,
            key,
        )

        self._runtime.pop(
            (provider, key),
            None,
        )

    @staticmethod
    def _from_keyring(
        provider: str,
        key: str,
    ) -> str | None:
        try:
            import keyring
        except ImportError:
            return None

        try:
            return keyring.get_password(
                f"orbitoby:{provider}",
                key,
            )
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _from_colab(
        env_name: str,
    ) -> str | None:
        try:
            from google.colab import userdata
        except ImportError:
            return None

        try:
            value = userdata.get(env_name)
        except Exception:  # noqa: BLE001
            return None

        return value or None

    def _from_dotenv(
        self,
        env_name: str,
    ) -> str | None:
        if not self.allow_dotenv or not self.dotenv_path.exists():
            return None

        value = dotenv_values(self.dotenv_path).get(env_name)

        return str(value) if value else None

    def resolve(
        self,
        provider: str,
        key: str,
        *,
        env_name: str | None = None,
    ) -> CredentialResult | None:
        provider, key = self._normalize(
            provider,
            key,
        )

        runtime = self._runtime.get((provider, key))

        if runtime:
            return CredentialResult(
                runtime,
                "runtime",
            )

        keyring_value = self._from_keyring(
            provider,
            key,
        )

        if keyring_value:
            return CredentialResult(
                keyring_value,
                "keyring",
            )

        env_name = env_name or self.env_name(
            provider,
            key,
        )

        environment = os.getenv(env_name)

        if environment:
            return CredentialResult(
                environment,
                "environment",
            )

        colab = self._from_colab(env_name)

        if colab:
            return CredentialResult(
                colab,
                "colab",
            )

        dotenv = self._from_dotenv(env_name)

        if dotenv:
            return CredentialResult(
                dotenv,
                "dotenv",
            )

        return None

    def get(
        self,
        provider: str,
        key: str,
        *,
        env_name: str | None = None,
        required: bool = False,
    ) -> str | None:
        result = self.resolve(
            provider,
            key,
            env_name=env_name,
        )

        if result is None:
            if required:
                raise RuntimeError(f"Credential not configured: {provider}/{key}")

            return None

        return result.value

    def status(
        self,
        provider: str,
        keys: tuple[str, ...],
    ) -> dict[str, dict[str, object]]:
        report = {}

        for key in keys:
            result = self.resolve(
                provider,
                key,
            )

            report[key] = {
                "configured": (result is not None),
                "source": (result.source if result else None),
            }

        return report

    @staticmethod
    def set_keyring(
        provider: str,
        key: str,
        value: str,
    ) -> None:
        try:
            import keyring
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional 'keyring' package to store OS credentials."
            ) from exc

        keyring.set_password(
            f"orbitoby:{provider}",
            key,
            value,
        )

    @staticmethod
    def delete_keyring(
        provider: str,
        key: str,
    ) -> None:
        try:
            import keyring
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional 'keyring' package to manage OS credentials."
            ) from exc

        try:
            keyring.delete_password(
                f"orbitoby:{provider}",
                key,
            )
        except keyring.errors.PasswordDeleteError:
            # Deleting an already-absent credential is idempotent.
            return


_TRUE_VALUES = frozenset(
    {
        "1",
        "true",
        "yes",
        "on",
    }
)


def default_credential_manager() -> CredentialManager:
    """Create Orbitoby's default credential resolver.

    Local .env loading is intentionally opt-in through
    ORBITOBY_ALLOW_DOTENV=1. Importing Orbitoby never loads .env.
    """
    raw = os.getenv(
        "ORBITOBY_ALLOW_DOTENV",
        "",
    )

    allow_dotenv = raw.strip().lower() in _TRUE_VALUES

    return CredentialManager(allow_dotenv=allow_dotenv)
