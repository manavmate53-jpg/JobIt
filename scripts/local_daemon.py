#!/usr/bin/env python3
"""JobIt Local Autonomous Background Daemon.

Runs continuously on your local Mac using your residential IP and persistent browser session:
- Executes Engine YANG (outreach, shadow engagement, connections) every 3 hours
- Executes Engine YING (reconnaissance, target hiring trends, teardowns) every 6 hours
- Scans inbox for recruiter responses and interview invites every 1 hour
- Automatically evaluates and applies to newly discovered high-fit jobs
"""

import datetime
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

LOG_FILE = REPO_ROOT / "reports" / "local_daemon.log"
os.makedirs(REPO_ROOT / "reports", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (DAEMON) %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("local_daemon")

RUNNING = True


def handle_shutdown(signum, frame):
    global RUNNING
    logger.info(f"Received signal {signum}. Shutting down daemon gracefully...")
    RUNNING = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def run_command(cmd_list, description):
    logger.info(f"Starting: {description} (cmd: {' '.join(cmd_list)})")
    try:
        start_t = time.time()
        res = subprocess.run(
            cmd_list,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        elapsed = round(time.time() - start_t, 2)
        if res.returncode == 0:
            logger.info(f"Completed {description} in {elapsed}s.")
        else:
            logger.warning(
                f"{description} exited with code {res.returncode} in {elapsed}s. Error: {res.stderr[:300]}"
            )
    except subprocess.TimeoutExpired:
        logger.error(f"{description} timed out after 600 seconds.")
    except Exception as e:
        logger.error(f"Unexpected error running {description}: {e}")


def main():
    logger.info("=" * 70)
    logger.info("⚡ JOBIT AUTONOMOUS LOCAL DAEMON INITIATED")
    logger.info(f"Workspace: {REPO_ROOT}")
    logger.info(f"Log Destination: {LOG_FILE}")
    logger.info("Schedule: YANG (every 3h) | YING (every 6h) | Inbox Check (every 1h)")
    logger.info("=" * 70)

    last_yang = 0.0
    last_ying = 0.0
    last_inbox = 0.0

    YANG_INTERVAL = 3 * 3600  # 3 hours
    YING_INTERVAL = 6 * 3600  # 6 hours
    INBOX_INTERVAL = 1 * 3600  # 1 hour

    # Run initial cycle immediately upon launch
    python_bin = sys.executable

    while RUNNING:
        now = time.time()

        # 1. Inbox & Reply Check (every 1 hour)
        if now - last_inbox >= INBOX_INTERVAL:
            run_command(
                [python_bin, "cli.py", "check-replies"],
                "Inbox Recruiter Reply Monitor",
            )
            last_inbox = now

        # 2. Engine YANG: Outreach & Execution (every 3 hours)
        if now - last_yang >= YANG_INTERVAL:
            run_command(
                [python_bin, "engines/yang_execution.py", "--live"],
                "Engine YANG (3-Hour Outreach & Execution)",
            )
            last_yang = now

        # 3. Engine YING: Reconnaissance (every 6 hours)
        if now - last_ying >= YING_INTERVAL:
            run_command(
                [python_bin, "engines/ying_recon.py"],
                "Engine YING (6-Hour Reconnaissance)",
            )
            last_ying = now

        # Heartbeat sleep for 60 seconds
        for _ in range(60):
            if not RUNNING:
                break
            time.sleep(1)

    logger.info("Daemon has terminated. Goodbye.")


if __name__ == "__main__":
    main()
