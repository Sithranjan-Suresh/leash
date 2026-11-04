"""In-process pub/sub feeding the SSE stream."""
import queue
import threading

_subs = []
_lock = threading.Lock()
_history = []


def publish(kind, data):
    evt = {"type": kind, "data": data}
    with _lock:
        _history.append(evt)
        del _history[:-200]
        for q in list(_subs):
            q.put(evt)


def subscribe(replay=False):
    q = queue.Queue()
    with _lock:
        if replay:
            for e in _history:
                q.put(e)
        _subs.append(q)
    return q


def unsubscribe(q):
    with _lock:
        if q in _subs:
            _subs.remove(q)
