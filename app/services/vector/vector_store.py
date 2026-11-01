"""Chroma vector store with process-safe lifecycle management."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import threading
from typing import Any, Iterator, Optional

from filelock import FileLock, Timeout

from app.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
POI_COLLECTIONS = {"attractions", "restaurants", "hotels"}


def _create_persistent_client(path: Path) -> Any:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    return chromadb.PersistentClient(
        path=str(path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


class VectorStoreError(RuntimeError):
    """Base error for local vector-store lifecycle failures."""


class VectorStoreBusyError(VectorStoreError):
    """Raised when another process owns the local Chroma directory."""


class VectorStoreCorruptError(VectorStoreError):
    """Raised when an existing Chroma collection cannot be read consistently."""


@dataclass(frozen=True)
class VectorStoreHealth:
    status: str
    collections: dict[str, int] = field(default_factory=dict)
    error: str | None = None


def resolve_persist_dir(persist_dir: str | Path | None = None) -> Path:
    configured = Path(persist_dir or settings.CHROMA_PERSIST_DIR).expanduser()
    if configured.is_absolute():
        return configured.resolve()
    return (PROJECT_ROOT / configured).resolve()


def lock_path_for(persist_dir: str | Path | None = None) -> Path:
    path = resolve_persist_dir(persist_dir)
    lock_name = (
        f"{path.name}.lock"
        if path.name.startswith(".")
        else f".{path.name}.lock"
    )
    return path.parent / lock_name


def _busy_message(path: Path) -> str:
    return (
        f"Chroma 数据目录正在被其他进程使用: {path}。"
        "请先停止后端、灌数或重建进程，再重试。"
    )


@contextmanager
def acquire_vector_lock(
    persist_dir: str | Path | None = None,
    timeout: float | None = None,
) -> Iterator[FileLock]:
    path = resolve_persist_dir(persist_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path_for(path)))
    try:
        lock.acquire(
            timeout=(
                settings.CHROMA_LOCK_TIMEOUT_SECONDS
                if timeout is None
                else timeout
            )
        )
    except Timeout as exc:
        raise VectorStoreBusyError(_busy_message(path)) from exc
    try:
        yield lock
    finally:
        lock.release()


class VectorStore:
    """Process-safe wrapper around one local Chroma ``PersistentClient``."""

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        lock_timeout: float | None = None,
    ) -> None:
        self.persist_dir = resolve_persist_dir(persist_dir)
        self.lock_timeout = (
            settings.CHROMA_LOCK_TIMEOUT_SECONDS
            if lock_timeout is None
            else lock_timeout
        )
        self._client: Any | None = None
        self._process_lock: FileLock | None = None
        self._state_lock = threading.RLock()
        self._health = VectorStoreHealth(status="empty")

    @property
    def client(self) -> Any:
        return self.open()

    @property
    def health(self) -> VectorStoreHealth:
        return self._health

    def open(self) -> Any:
        with self._state_lock:
            if self._client is not None:
                return self._client

            self.persist_dir.parent.mkdir(parents=True, exist_ok=True)
            process_lock = FileLock(str(lock_path_for(self.persist_dir)))
            try:
                process_lock.acquire(timeout=self.lock_timeout)
            except Timeout as exc:
                self._health = VectorStoreHealth(
                    status="unhealthy",
                    error=_busy_message(self.persist_dir),
                )
                raise VectorStoreBusyError(self._health.error) from exc

            try:
                client = _create_persistent_client(self.persist_dir)
            except Exception:
                process_lock.release()
                raise

            self._process_lock = process_lock
            self._client = client
            return client

    def close(self) -> None:
        with self._state_lock:
            client = self._client
            process_lock = self._process_lock
            self._client = None
            self._process_lock = None
            try:
                if client is not None:
                    close = getattr(client, "close", None)
                    if close is not None:
                        close()
            finally:
                if process_lock is not None and process_lock.is_locked:
                    process_lock.release()

    def validate(self) -> VectorStoreHealth:
        try:
            client = self.open()
            names = [collection.name for collection in client.list_collections()]
            counts = {
                name: client.get_collection(name=name).count()
                for name in names
            }
        except VectorStoreBusyError:
            raise
        except Exception as exc:
            self._health = VectorStoreHealth(
                status="unhealthy",
                error=str(exc),
            )
            raise VectorStoreCorruptError(
                f"Chroma 索引校验失败: {exc}。"
                "请停止后端后运行 python scripts/rebuild_vectors.py。"
            ) from exc

        self._health = VectorStoreHealth(
            status=(
                "healthy"
                if POI_COLLECTIONS.issubset(counts)
                else "empty"
            ),
            collections=counts,
        )
        return self._health

    def get_or_create_collection(self, name: str) -> Any:
        return self.client.get_or_create_collection(name=name)

    def list_collections(self) -> list[str]:
        return [collection.name for collection in self.client.list_collections()]

    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(name=name)

    def delete(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        where: dict | None = None,
    ) -> None:
        if not ids and not where:
            return
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=ids, where=where)

    def add(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        collection = self.get_or_create_collection(collection_name)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict] = None,
    ) -> dict:
        collection = self.get_or_create_collection(collection_name)
        try:
            return collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
            )
        except Exception as exc:
            self._health = VectorStoreHealth(
                status="unhealthy",
                collections=self._health.collections,
                error=str(exc),
            )
            raise

    def count(self, collection_name: str) -> int:
        return self.get_or_create_collection(collection_name).count()

    def __enter__(self) -> "VectorStore":
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


vector_store = VectorStore()
