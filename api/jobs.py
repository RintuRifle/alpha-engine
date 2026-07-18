"""
In-process background job manager.

Replaces Redis/Celery with a simple ThreadPoolExecutor — good enough for
a single-instance deployment (Render). Jobs report progress that can be
polled via REST or streamed via WebSocket.
"""

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional


class JobManager:
    def __init__(self, max_workers: int = 2, ttl_seconds: int = 3600):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def submit(self, kind: str, fn: Callable[..., Any], **kwargs) -> str:
        """Submit fn(progress=callback, **kwargs) as a background job."""
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._gc()
            self._jobs[job_id] = {
                "id": job_id,
                "kind": kind,
                "status": "queued",
                "progress": 0,
                "message": "Queued...",
                "result": None,
                "error": None,
                "created_at": time.time(),
            }

        def progress(pct: int, message: str = ""):
            with self._lock:
                job = self._jobs.get(job_id)
                if job and job["status"] == "running":
                    job["progress"] = int(pct)
                    if message:
                        job["message"] = message

        def runner():
            with self._lock:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting..."
            try:
                result = fn(progress=progress, **kwargs)
                with self._lock:
                    self._jobs[job_id].update(
                        status="done", progress=100, message="Complete", result=result
                    )
            except Exception as e:
                with self._lock:
                    self._jobs[job_id].update(
                        status="error",
                        message=str(e),
                        error=f"{e}\n{traceback.format_exc(limit=3)}",
                    )

        self._executor.submit(runner)
        return job_id

    def get(self, job_id: str, include_result: bool = True) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            out = {k: v for k, v in job.items() if k not in ("result",)}
            if include_result and job["status"] == "done":
                out["result"] = job["result"]
            return out

    def _gc(self):
        """Drop finished jobs older than TTL."""
        now = time.time()
        stale = [
            jid for jid, j in self._jobs.items()
            if j["status"] in ("done", "error") and now - j["created_at"] > self._ttl
        ]
        for jid in stale:
            del self._jobs[jid]


manager = JobManager()
