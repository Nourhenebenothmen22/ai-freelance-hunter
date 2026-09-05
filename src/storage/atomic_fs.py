"""Atomic and Thread-Safe Filesystem Operations.

Provides cross-platform atomic writes and file locking for JSON and JSONL.
Strictly NO databases used.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    import portalocker
    def _create_lock(lock_path: Path):
        return portalocker.Lock(str(lock_path), timeout=10)
except ImportError:
    from filelock import FileLock
    def _create_lock(lock_path: Path):
        return FileLock(str(lock_path), timeout=10)


class AtomicFS:
    """Handles atomic read/write operations with file locks."""

    @staticmethod
    def _get_lock(path: Path):
        """Create a cross-platform lock associated with a file path."""
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        return _create_lock(lock_path)

    @classmethod
    def write_atomic(cls, file_path: Path, data_str: str) -> None:
        """Write content atomically using a temporary file and atomic replace."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with cls._get_lock(file_path):
            temp_dir = file_path.parent
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=temp_dir, delete=False) as tf:
                tf.write(data_str)
                tf.flush()
                os.fsync(tf.fileno())
                temp_name = tf.name

            # Atomic replace (guaranteed atomic on POSIX and Windows in Python 3.3+)
            os.replace(temp_name, file_path)

    @classmethod
    def read_json(cls, file_path: Path, default: Any = None) -> Any:
        """Read and parse a JSON file with safe locking."""
        file_path = Path(file_path)
        if not file_path.exists():
            return default

        with cls._get_lock(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return default

    @classmethod
    def write_json(cls, file_path: Path, data: Any, indent: int = 2) -> None:
        """Atomically write Python data as formatted JSON."""
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)
        cls.write_atomic(file_path, json_str)

    @classmethod
    def append_jsonl(cls, file_path: Path, item: Dict[str, Any]) -> None:
        """Safely append a single JSON line to a .jsonl file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        line = json.dumps(item, ensure_ascii=False) + "\n"
        with cls._get_lock(file_path):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())

    @classmethod
    def read_jsonl(cls, file_path: Path) -> List[Dict[str, Any]]:
        """Read all lines from a .jsonl file."""
        file_path = Path(file_path)
        if not file_path.exists():
            return []

        results = []
        with cls._get_lock(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return results
