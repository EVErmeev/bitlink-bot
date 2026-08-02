"""Thread-safe async connection check runner with UI poller."""
import queue
import threading


class ConnectionCheckRunner:
    def __init__(self, frame):
        self._frame = frame
        self._result_queue = queue.Queue()
        self._running = {}
        self._polling = False
        self._callbacks = {}  # check_id → callback

    def start_check(self, check_id, worker_fn, on_complete):
        if check_id in self._running and self._running[check_id]:
            return False
        self._running[check_id] = True

        def runner():
            try:
                result = worker_fn()
            except Exception as e:
                from services.connection_checks import make_error_result
                result = make_error_result(check_id, str(e))
            finally:
                self._result_queue.put((check_id, result))

        self._callbacks[check_id] = on_complete
        threading.Thread(target=runner, daemon=True).start()
        if not self._polling:
            self._start_polling()
        return True

    def _start_polling(self):
        self._polling = True
        self._frame.after(100, self._poll_results)

    def _poll_results(self):
        try:
            while True:
                check_id, result = self._result_queue.get_nowait()
                self._running[check_id] = False
                cb = self._callbacks.pop(check_id, None)
                if cb:
                    cb(check_id, result)
        except queue.Empty:
            pass

        if any(self._running.values()):
            self._frame.after(100, self._poll_results)
        else:
            self._polling = False

    def is_running(self, check_id):
        return self._running.get(check_id, False)
