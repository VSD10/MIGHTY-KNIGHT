import threading
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class EngineQueueManager:
    """
    Rule 6: Non-Blocking Engine Execution, Request Queuing, and Thread Safety.
    
    Guarantees:
    1. UI Responsiveness: Engine execution runs asynchronously in a worker thread.
       All pages remain viewable and responsive. Existing data is immediately served.
    2. Request Queuing: User actions or mutation requests submitted during engine execution
       are queued in FIFO order and processed safely upon engine completion.
    3. Thread Safety: RLock ensures synchronized access, transaction safety, and no race conditions.
    4. Auto-Reconciliation: Queued mutations are reconciled against the freshly generated schedule.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EngineQueueManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.is_running = False
        self.current_job: Optional[Dict[str, Any]] = None
        self.pending_requests: List[Dict[str, Any]] = []
        self.completed_jobs: List[Dict[str, Any]] = []
        self.request_handlers: Dict[str, Callable] = {}

    @property
    def is_engine_running(self) -> bool:
        with self._lock:
            return self.is_running

    def get_queued_count(self) -> int:
        with self._lock:
            return len(self.pending_requests)

    def reset_state(self):
        with self._lock:
            self.is_running = False
            self.current_job = None
            self.pending_requests.clear()

    def register_handler(self, request_type: str, handler: Callable):
        with self._lock:
            self.request_handlers[request_type] = handler

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_running": self.is_running,
                "current_job": dict(self.current_job) if self.current_job else None,
                "queued_count": len(self.pending_requests),
                "queued_requests": [
                    {
                        "request_id": r["request_id"],
                        "request_type": r["request_type"],
                        "created_at": r["created_at"],
                        "status": r.get("status", "queued")
                    }
                    for r in self.pending_requests
                ]
            }

    def submit_engine_job(
        self,
        job_fn: Callable[[], Any],
        month: str = "2026-10",
        on_complete: Optional[Callable[[Any], None]] = None
    ) -> Dict[str, Any]:
        with self._lock:
            if self.is_running:
                return {
                    "status": "already_running",
                    "job_id": self.current_job.get("job_id") if self.current_job else "UNKNOWN",
                    "message": "Engine is already executing in background. All pages remain active and accessible."
                }

            job_id = f"JOB_{uuid.uuid4().hex[:8].upper()}"
            self.is_running = True
            self.current_job = {
                "job_id": job_id,
                "month": month,
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }

        def _worker():
            result = None
            error = None
            try:
                logger.info(f"[EngineQueueManager] Starting engine background job {job_id}...")
                result = job_fn()
                if on_complete:
                    on_complete(result)
            except Exception as e:
                logger.exception(f"[EngineQueueManager] Engine job {job_id} failed: {e}")
                error = str(e)
            finally:
                self._post_engine_execution(job_id, result, error, month)

        thread = threading.Thread(target=_worker, name=f"EngineWorker-{job_id}", daemon=True)
        thread.start()

        return {
            "status": "started",
            "job_id": job_id,
            "month": month,
            "message": "Engine execution started in background. All pages remain viewable and responsive."
        }

    def queue_or_execute(
        self,
        request_type: str,
        payload: Dict[str, Any],
        execute_fn: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> Dict[str, Any]:
        """
        If engine is currently executing, safely queues the mutation request.
        Otherwise, executes it immediately under the thread lock.
        """
        with self._lock:
            fn = execute_fn or self.request_handlers.get(request_type)
            if not fn:
                raise ValueError(f"No handler registered for request type: {request_type}")

            if self.is_running:
                req_id = f"REQ_{uuid.uuid4().hex[:8].upper()}"
                queued_item = {
                    "request_id": req_id,
                    "request_type": request_type,
                    "payload": payload,
                    "execute_fn": fn,
                    "created_at": datetime.now().isoformat(),
                    "status": "queued"
                }
                self.pending_requests.append(queued_item)
                logger.info(f"[EngineQueueManager] Queued request {req_id} ({request_type}) during active engine run.")
                return {
                    "status": "queued",
                    "request_id": req_id,
                    "queued_position": len(self.pending_requests),
                    "message": "Scheduling engine is currently running. Your request is queued and will be processed immediately after execution completes."
                }
            else:
                # Not running: execute immediately under lock
                res = fn(payload)
                return {
                    "status": "executed",
                    "result": res
                }

    def _post_engine_execution(self, job_id: str, result: Any, error: Optional[str], month: str):
        processed_queue_results = []
        with self._lock:
            job_record = dict(self.current_job or {})
            job_record["completed_at"] = datetime.now().isoformat()
            job_record["error"] = error
            job_record["status"] = "failed" if error else "completed"
            self.completed_jobs.append(job_record)

            # Drain queued requests in FIFO order
            logger.info(f"[EngineQueueManager] Engine job {job_id} done. Draining {len(self.pending_requests)} queued request(s)...")
            while self.pending_requests:
                req = self.pending_requests.pop(0)
                req_id = req["request_id"]
                req_type = req["request_type"]
                fn = req["execute_fn"]
                payload = req["payload"]
                try:
                    logger.info(f"[EngineQueueManager] Processing queued request {req_id} ({req_type})...")
                    r_res = fn(payload)
                    processed_queue_results.append({"request_id": req_id, "status": "success", "result": r_res})
                except Exception as q_err:
                    logger.exception(f"[EngineQueueManager] Queued request {req_id} failed: {q_err}")
                    processed_queue_results.append({"request_id": req_id, "status": "error", "error": str(q_err)})

            self.is_running = False
            self.current_job = None

        # Emit schedule change event after all queued mutations have reconciled
        try:
            from app.main import ScheduleEventBus
            ScheduleEventBus.emit_change(month)
        except Exception as bus_err:
            logger.warning(f"[EngineQueueManager] Failed to emit change: {bus_err}")

# Authoritative global instance
queue_manager = EngineQueueManager()
