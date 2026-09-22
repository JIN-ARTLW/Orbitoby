from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SourceAdapter(ABC):
    """
    모든 외부 데이터 소스가 따라야 하는 공통 인터페이스.
    """

    name: str
    datasets: tuple[str, ...] = ()

    @abstractmethod
    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        """
        외부 데이터 소스의 raw response를 bytes로 반환.
        """
        raise NotImplementedError

    @abstractmethod
    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        """
        raw response를 Python record 형식으로 변환.
        """
        raise NotImplementedError