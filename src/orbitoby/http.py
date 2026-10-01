from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_REDIRECT_CODES = {
    301,
    302,
    303,
    307,
    308,
}

_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
}


class SafeHttpClient:
    """HTTPS client with provider host allowlisting and payload limits."""

    def __init__(
        self,
        *,
        allowed_hosts: Iterable[str],
        user_agent: str = "Orbitoby/0.1.0",
        connect_timeout: float = 10.0,
        read_timeout: float = 90.0,
        max_bytes: int = 128 * 1024 * 1024,
        max_redirects: int = 5,
        retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.allowed_hosts = {host.lower().strip(".") for host in allowed_hosts if host}

        if not self.allowed_hosts:
            raise ValueError("allowed_hosts must not be empty")

        if max_bytes <= 0:
            raise ValueError("max_bytes must be > 0")

        self.timeout = (
            connect_timeout,
            read_timeout,
        )
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

        self.session = session if session is not None else requests.Session()

        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )

        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=0.5,
            status_forcelist=(
                429,
                500,
                502,
                503,
                504,
            ),
            allowed_methods=(
                "GET",
                "HEAD",
                "OPTIONS",
            ),
            respect_retry_after_header=True,
        )

        adapter = HTTPAdapter(max_retries=retry)

        self.session.mount(
            "https://",
            adapter,
        )

    def validate_url(
        self,
        url: str,
    ) -> str:
        parsed = urlparse(url)

        if parsed.scheme.lower() != "https":
            raise ValueError("Orbitoby network sources require HTTPS.")

        host = (parsed.hostname or "").lower().strip(".")

        if host not in self.allowed_hosts:
            raise ValueError(f"Host not allowed for this source: {host!r}")

        if parsed.username or parsed.password:
            raise ValueError("Credentials must not be embedded in URLs.")

        return url

    def _read_limited(
        self,
        response: requests.Response,
    ) -> bytes:
        content_length = response.headers.get("Content-Length")

        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = None

            if declared is not None and declared > self.max_bytes:
                raise RuntimeError("Response exceeds configured payload limit.")

        chunks = []
        size = 0

        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue

            size += len(chunk)

            if size > self.max_bytes:
                raise RuntimeError("Response exceeds configured payload limit.")

            chunks.append(chunk)

        return b"".join(chunks)

    @staticmethod
    def _strip_sensitive_headers(
        headers: dict[str, str],
    ) -> dict[str, str]:
        return {
            key: value
            for key, value in headers.items()
            if key.lower() not in _SENSITIVE_HEADERS
        }

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> bytes:
        method = method.upper()

        if method not in {
            "GET",
            "POST",
            "HEAD",
        }:
            raise ValueError(f"Unsupported HTTP method: {method}")

        current_url = self.validate_url(url)

        current_headers = dict(headers or {})

        for redirect_index in range(self.max_redirects + 1):
            response = self.session.request(
                method,
                current_url,
                headers=current_headers,
                allow_redirects=False,
                stream=True,
                timeout=self.timeout,
                verify=True,
                **kwargs,
            )

            try:
                if response.status_code not in _REDIRECT_CODES:
                    response.raise_for_status()

                    if method == "HEAD":
                        return b""

                    return self._read_limited(response)

                if redirect_index >= self.max_redirects:
                    raise RuntimeError("Too many HTTP redirects.")

                location = response.headers.get("Location")

                if not location:
                    raise RuntimeError("Redirect response has no Location header.")

                next_url = urljoin(
                    current_url,
                    location,
                )

                self.validate_url(next_url)

                old_host = urlparse(current_url).hostname

                new_host = urlparse(next_url).hostname

                if old_host != new_host:
                    current_headers = self._strip_sensitive_headers(current_headers)

                # RFC-style redirect behaviour for POST → GET.
                if response.status_code == 303 and method != "HEAD":
                    method = "GET"

                    kwargs.pop(
                        "data",
                        None,
                    )
                    kwargs.pop(
                        "json",
                        None,
                    )

                current_url = next_url

                # Query params belong to the original request.
                kwargs.pop(
                    "params",
                    None,
                )

            finally:
                response.close()

        raise RuntimeError("HTTP request failed unexpectedly.")

    def get(
        self,
        url: str,
        **kwargs,
    ) -> bytes:
        return self.request(
            "GET",
            url,
            **kwargs,
        )

    def post(
        self,
        url: str,
        **kwargs,
    ) -> bytes:
        return self.request(
            "POST",
            url,
            **kwargs,
        )
