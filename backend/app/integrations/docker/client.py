import asyncio
from typing import Any

import docker
import requests
from docker.errors import DockerException, NotFound

from app.integrations.docker.exceptions import (
    DockerContainerNotFoundError,
    DockerPermissionError,
    DockerTimeoutError,
    DockerUnavailableError,
)


class DockerClient:
    """Thin async wrapper over the official Docker SDK, targeting the LOCAL
    Docker Engine on this host only (no remote Docker, no Kubernetes, no
    ECS). Every SDK call is blocking, so it's offloaded to a thread.

    Accepts an injected `docker_client` so tests never need a real daemon."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 10,
        docker_client: Any | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._client = docker_client

    def _get_client(self):
        if self._client is None:
            try:
                self._client = (
                    docker.DockerClient(base_url=self._base_url, timeout=self._timeout)
                    if self._base_url
                    else docker.from_env(timeout=self._timeout)
                )
            except DockerException as exc:
                raise DockerUnavailableError(f"Could not connect to Docker daemon: {exc}") from exc
        return self._client

    async def _run(self, fn, *args, **kwargs):
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except NotFound as exc:
            raise DockerContainerNotFoundError(str(exc)) from exc
        except PermissionError as exc:
            raise DockerPermissionError(str(exc)) from exc
        except requests.exceptions.Timeout as exc:
            raise DockerTimeoutError(str(exc)) from exc
        except DockerException as exc:
            raise DockerUnavailableError(str(exc)) from exc

    async def health(self) -> bool:
        return await self._run(self._health_sync)

    def _health_sync(self) -> bool:
        return bool(self._get_client().ping())

    async def list_containers(self, all: bool = True) -> list:
        return await self._run(self._list_containers_sync, all)

    def _list_containers_sync(self, all: bool) -> list:
        return self._get_client().containers.list(all=all)

    async def get_container(self, container_id: str):
        return await self._run(self._get_container_sync, container_id)

    def _get_container_sync(self, container_id: str):
        return self._get_client().containers.get(container_id)

    async def container_stats(self, container_id: str) -> dict:
        return await self._run(self._container_stats_sync, container_id)

    def _container_stats_sync(self, container_id: str) -> dict:
        return self._get_client().containers.get(container_id).stats(stream=False)

    async def container_logs(self, container_id: str, tail: int, timestamps: bool) -> bytes:
        return await self._run(self._container_logs_sync, container_id, tail, timestamps)

    def _container_logs_sync(self, container_id: str, tail: int, timestamps: bool) -> bytes:
        container = self._get_client().containers.get(container_id)
        return container.logs(tail=tail, timestamps=timestamps)

    async def restart_container(self, container_id: str, timeout: int = 10) -> None:
        await self._run(self._restart_container_sync, container_id, timeout)

    def _restart_container_sync(self, container_id: str, timeout: int) -> None:
        # Safe restart only - SIGTERM then SIGKILL after `timeout`s. Never kill+remove+prune.
        self._get_client().containers.get(container_id).restart(timeout=timeout)
