"""
Engine Queue Manager (Rule 5 & Rule 6)
Provides non-blocking, thread-safe asynchronous task execution and request queuing
for the Mighty Knight Scheduling Engine.
- Pages remain viewable and responsive while tasks process.
- Background worker processes tasks sequentially with dependency-aware reconciliation.
- Auto-pushes updates to connected clients via ScheduleEventBus upon completion.
"""

import threading
import queue
import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

logger = logging.getLogger("engine_queue")

class EngineTask:
    def __init__(self, task_type: str, payload: Dict[str, Any], task_id: Optional[str] = None):
        self.task_id = task_id or f"TASK_{uuid.uuid4().hex[:8].upper()}"
        self.task_type = task_type
        self.payload = payload
        self.status = "queued"  # queued | running | completed | failed
        self.created_at = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.execution_duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_duration_sec": round(self.execution_duration_sec, 3),
            "result": self.result,
            "error": self.error
        }

class EngineQueueManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EngineQueueManager, cls).__new__(cls)
                cls._instance._init_queue()
            return cls._instance

    def _init_queue(self):
        self._task_queue = queue.Queue()
        self._tasks: Dict[str, EngineTask] = {}
        self._handlers: Dict[str, Callable] = {}
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._is_running = True
        self._current_task: Optional[EngineTask] = None
        self._worker_thread.start()

    def register_handler(self, task_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Registers a callable execution handler for a specific task type."""
        self._handlers[task_type] = handler

    def enqueue_task(self, task_type: str, payload: Dict[str, Any]) -> EngineTask:
        """
        Enqueues an engine task with request reconciliation.
        If a duplicate task is already queued for the same scope, reconciles it.
        """
        with self._lock:
            # Reconcile duplicate pending tasks of same type and month
            month = payload.get("month", "2026-10")
            for t in self._tasks.values():
                if t.status == "queued" and t.task_type == task_type and t.payload.get("month") == month:
                    # Update payload of existing queued task rather than duplicating
                    t.payload.update(payload)
                    logger.info(f"Reconciled existing queued task {t.task_id} for month {month}")
                    return t

            task = EngineTask(task_type, payload)
            self._tasks[task.task_id] = task
            self._task_queue.put(task)
            logger.info(f"Enqueued task {task.task_id} of type {task_type}")
            return task

    def get_task(self, task_id: str) -> Optional[EngineTask]:
        return self._tasks.get(task_id)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_busy": self._current_task is not None,
                "current_task": self._current_task.to_dict() if self._current_task else None,
                "pending_count": self._task_queue.qsize(),
                "completed_count": sum(1 for t in self._tasks.values() if t.status == "completed"),
                "failed_count": sum(1 for t in self._tasks.values() if t.status == "failed")
            }

    def _worker_loop(self):
        while self._is_running:
            try:
                task = self._task_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            self._current_task = task
            task.status = "running"
            task.started_at = datetime.now().isoformat()
            t0 = time.time()
            logger.info(f"Engine worker executing task {task.task_id} ({task.task_type})")

            try:
                handler = self._handlers.get(task.task_type)
                if handler:
                    res = handler(task.payload)
                    task.result = res
                    task.status = "completed"
                else:
                    task.error = f"No handler registered for task type '{task.task_type}'"
                    task.status = "failed"
            except Exception as e:
                logger.exception(f"Error executing engine task {task.task_id}: {e}")
                task.error = str(e)
                task.status = "failed"
            finally:
                t1 = time.time()
                task.execution_duration_sec = t1 - t0
                task.completed_at = datetime.now().isoformat()
                self._current_task = None
                self._task_queue.task_done()

                # Automatically push SSE update to all connected frontend pages
                try:
                    from app.engine.effective_schedule_service import ScheduleEventBus
                    month = task.payload.get("month", "2026-10")
                    ScheduleEventBus.emit_change(month)
                except Exception as sse_err:
                    logger.warning(f"Could not emit SSE for completed task {task.task_id}: {sse_err}")

# Global singleton
engine_queue = EngineQueueManager()
