import os
import sqlite3
from collections.abc import Iterator, Sequence
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple, RunnableConfig, get_checkpoint_id, get_checkpoint_metadata
from langgraph.checkpoint.memory import WRITES_IDX_MAP


class SqliteCheckpointer(BaseCheckpointSaver[str]):
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    checkpoint_blob BLOB NOT NULL,
                    metadata_type TEXT NOT NULL,
                    metadata_blob BLOB NOT NULL,
                    parent_checkpoint_id TEXT,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blobs (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    version TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_blob BLOB NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_blob BLOB NOT NULL,
                    task_path TEXT NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
                """
            )

    def _load_blobs(self, thread_id: str, checkpoint_ns: str, channel_versions: dict[str, str]) -> dict[str, Any]:
        if not channel_versions:
            return {}
        out: dict[str, Any] = {}
        with self._connect() as conn:
            for channel, version in channel_versions.items():
                row = conn.execute(
                    """
                    SELECT value_type, value_blob
                    FROM blobs
                    WHERE thread_id = ? AND checkpoint_ns = ? AND channel = ? AND version = ?
                    """,
                    (thread_id, checkpoint_ns, channel, version),
                ).fetchone()
                if row is None:
                    continue
                if row[0] == "empty":
                    continue
                out[channel] = self.serde.loads_typed((row[0], row[1]))
        return out

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"]["checkpoint_ns"]
        checkpoint_id = get_checkpoint_id(config)
        with self._connect() as conn:
            if checkpoint_id:
                row = conn.execute(
                    """
                    SELECT checkpoint_id, checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, parent_checkpoint_id
                    FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                    """,
                    (thread_id, checkpoint_ns, checkpoint_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT checkpoint_id, checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, parent_checkpoint_id
                    FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ?
                    ORDER BY checkpoint_id DESC
                    LIMIT 1
                    """,
                    (thread_id, checkpoint_ns),
                ).fetchone()
            if row is None:
                return None

            checkpoint_id, c_type, c_blob, m_type, m_blob, parent_checkpoint_id = row
            checkpoint_: Checkpoint = self.serde.loads_typed((c_type, c_blob))
            metadata: CheckpointMetadata = self.serde.loads_typed((m_type, m_blob))
            writes_rows = conn.execute(
                """
                SELECT task_id, channel, value_type, value_blob, task_path
                FROM writes
                WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                ORDER BY task_id, idx
                """,
                (thread_id, checkpoint_ns, checkpoint_id),
            ).fetchall()

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            },
            checkpoint={
                **checkpoint_,
                "channel_values": self._load_blobs(thread_id, checkpoint_ns, checkpoint_["channel_versions"]),
            },
            metadata=metadata,
            pending_writes=[
                (task_id, channel, self.serde.loads_typed((v_type, v_blob)))
                for task_id, channel, v_type, v_blob, _task_path in writes_rows
            ],
            parent_config=(
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if config is None:
            return iter(())
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"]["checkpoint_ns"]
        before_id = get_checkpoint_id(before) if before else None
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT checkpoint_id, checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, parent_checkpoint_id
                FROM checkpoints
                WHERE thread_id = ? AND checkpoint_ns = ?
                ORDER BY checkpoint_id DESC
                """,
                (thread_id, checkpoint_ns),
            ).fetchall()

        out: list[CheckpointTuple] = []
        for checkpoint_id, c_type, c_blob, m_type, m_blob, parent_checkpoint_id in rows:
            if before_id and checkpoint_id >= before_id:
                continue
            checkpoint_: Checkpoint = self.serde.loads_typed((c_type, c_blob))
            metadata: CheckpointMetadata = self.serde.loads_typed((m_type, m_blob))
            if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                continue
            out.append(
                CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                        }
                    },
                    checkpoint={
                        **checkpoint_,
                        "channel_values": self._load_blobs(thread_id, checkpoint_ns, checkpoint_["channel_versions"]),
                    },
                    metadata=metadata,
                    parent_config=(
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_ns": checkpoint_ns,
                                "checkpoint_id": parent_checkpoint_id,
                            }
                        }
                        if parent_checkpoint_id
                        else None
                    ),
                    pending_writes=[],
                )
            )
            if limit is not None:
                limit -= 1
                if limit <= 0:
                    break
        return iter(out)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, str],
    ) -> RunnableConfig:
        c = checkpoint.copy()
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"]["checkpoint_ns"]
        values: dict[str, Any] = c.pop("channel_values")  # type: ignore[misc]

        with self._connect() as conn:
            for channel, version in new_versions.items():
                if channel in values:
                    v_type, v_blob = self.serde.dumps_typed(values[channel])
                else:
                    v_type, v_blob = ("empty", b"")
                conn.execute(
                    """
                    INSERT OR REPLACE INTO blobs(thread_id, checkpoint_ns, channel, version, value_type, value_blob)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (thread_id, checkpoint_ns, channel, str(version), v_type, v_blob),
                )

            c_type, c_blob = self.serde.dumps_typed(c)
            meta_obj = get_checkpoint_metadata(config, metadata)
            m_type, m_blob = self.serde.dumps_typed(meta_obj)
            parent_checkpoint_id = config["configurable"].get("checkpoint_id")
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints(
                    thread_id, checkpoint_ns, checkpoint_id,
                    checkpoint_type, checkpoint_blob,
                    metadata_type, metadata_blob,
                    parent_checkpoint_id
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint["id"],
                    c_type,
                    c_blob,
                    m_type,
                    m_blob,
                    parent_checkpoint_id,
                ),
            )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"]["checkpoint_ns"]
        checkpoint_id: str = config["configurable"]["checkpoint_id"]
        with self._connect() as conn:
            for idx, (channel, value) in enumerate(writes):
                mapped = WRITES_IDX_MAP.get(channel, idx)
                v_type, v_blob = self.serde.dumps_typed(value)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO writes(
                        thread_id, checkpoint_ns, checkpoint_id,
                        task_id, idx, channel,
                        value_type, value_blob, task_path
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        task_id,
                        int(mapped),
                        channel,
                        v_type,
                        v_blob,
                        task_path,
                    ),
                )
