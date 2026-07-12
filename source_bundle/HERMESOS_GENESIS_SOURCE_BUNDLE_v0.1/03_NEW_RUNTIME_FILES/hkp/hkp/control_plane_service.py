"""HKP Control Plane — Windows Service entry point.

Runs the Control Plane broker as a Windows service under LocalService.
All configuration is passed as command-line arguments (not registry env vars).

Phase A: shadow mode.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add hermes-agent root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hkp.broker_server as broker
from hkp.audit_ledger import get_ledger

logger = logging.getLogger("HKP.Service")


def resolve_home(home_arg: str | None) -> Path:
    """Resolve HERMES_HOME from argument. No env var fallback for security."""
    if home_arg:
        return Path(home_arg).expanduser().resolve()
    # Only used for standalone testing — service always passes --home
    return Path.home() / ".hermes"


def run_service(args: argparse.Namespace) -> None:
    """Run the Control Plane as a service (or standalone)."""
    hermes_home = resolve_home(args.home)
    log_dir = hermes_home / "hkp" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "control_plane.log"

    # Set HERMES_HOME for child modules (audit_ledger, credential_store, etc.)
    os.environ["HERMES_HOME"] = str(hermes_home)

    # Set emergency stop from argument (not from external env)
    if args.emergency_stop:
        os.environ["HKP_EMERGENCY_STOP"] = "true"

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [HKP] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler(),
        ],
    )

    mode = args.mode  # "shadow" or "enforcing"
    host = args.host
    port = args.port

    logger.info("=== HKP Control Plane Service ===")
    logger.info("Config source: command-line arguments")
    logger.info("Home: %s", hermes_home)
    logger.info("Host: %s:%d", host, port)
    logger.info("Mode: %s", mode)
    logger.info("Emergency stop: %s", args.emergency_stop)
    logger.info("Phase: A (Foundation)")
    logger.info("Log file: %s", log_file)

    try:
        broker.run_broker_forever(host=host, port=port, mode=mode)
    except Exception as exc:
        logger.critical("Broker service terminated: %s", exc)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="HKP Control Plane Broker")

    # All config passed as explicit arguments — NOT from environment/registry
    parser.add_argument("--mode", choices=["shadow", "enforcing"],
                        default="shadow",
                        help="Broker mode (Phase A: shadow)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Listen address (localhost only)")
    parser.add_argument("--port", type=int, default=9877,
                        help="Listen port")
    parser.add_argument("--home",
                        help="HERMES_HOME path (required for service mode)")
    parser.add_argument("--emergency-stop", action="store_true",
                        default=True,
                        help="Enable emergency stop flag")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level")
    parser.add_argument("--standalone", action="store_true",
                        help="Run in foreground (not as Windows service)")

    args = parser.parse_args()

    if not args.home and not args.standalone:
        print("ERROR: --home is required in service mode. Pass --standalone for testing.")
        sys.exit(1)

    run_service(args)


if __name__ == "__main__":
    main()
