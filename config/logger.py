import json
import logging
import uuid
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class JsonlHandler(TimedRotatingFileHandler):
    def __init__(self):
        today = datetime.now().strftime("%Y-%m-%d")
        super().__init__(
            filename=str(LOGS_DIR / f"requests_{today}.jsonl"),
            when="midnight",
            interval=1,
            backupCount=3,
            encoding="utf-8",
        )

    def emit(self, record):
        try:
            self.stream.write(record.getMessage() + "\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)


_handler = JsonlHandler()
_logger  = logging.getLogger("hr_chatbot")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_handler)
_logger.propagate = False


def log_request(
    emp_id: int,
    thread_id: str,
    original_query: str,
    rewritten_query: str,
    category: str,
    query_type: str,
    data_type: str | None,
    target_name: str,
    final_response: str,
):
    _logger.info(json.dumps({
        "request_id":      str(uuid.uuid4()),
        "timestamp":       datetime.now().isoformat(),
        "type":            "request",
        "emp_id":          emp_id,
        "thread_id":       thread_id,
        "original_query":  original_query,
        "rewritten_query": rewritten_query,
        "category":        category,
        "query_type":      query_type,
        "data_type":       data_type,
        "target_name":     target_name,
        "final_response":  final_response,
    }))


def log_error(
    emp_id: int | None,
    thread_id: str | None,
    original_query: str | None,
    error: Exception,
):
    _logger.info(json.dumps({
        "request_id":     str(uuid.uuid4()),
        "timestamp":      datetime.now().isoformat(),
        "type":           "error",
        "emp_id":         emp_id,
        "thread_id":      thread_id,
        "original_query": original_query,
        "error":          str(error),
    }))
