from threading import Event
from datetime import datetime
import time
from backend.persona.dreamlog import generate_dreamlog_entry

_STOP = Event()

def run_scheduler():
    print("[Scheduler] Started.")
    last_run_date = None

    while not _STOP.is_set():
        now = datetime.utcnow()
        today = now.date()

        if today != last_run_date and now.hour == 3:
            print("[Scheduler] Triggering Eden dreamlog …")
            log = generate_dreamlog_entry()
            print("[Eden] Dreamlog:\n", log["monologue"])
            last_run_date = today

        _STOP.wait(60)  # Sleep and check again every 60 sec

def stop_scheduler():
    _STOP.set()
