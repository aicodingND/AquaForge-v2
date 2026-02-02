"""
Unified Server Runner

This module provides a unified way to run the application with options for:
1. Reflex only (current mode)
2. FastAPI only (API-only mode)
3. Hybrid mode (both Reflex frontend + FastAPI backend on separate ports)

This is the foundation for migrating to a full FastAPI + React/Next.js stack.
"""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def run_fastapi(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """
    Run the standalone FastAPI server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
    """
    import uvicorn

    logger.info(f"🚀 Starting FastAPI server on http://{host}:{port}")
    logger.info(f"📚 API docs available at http://{host}:{port}/api/docs")

    uvicorn.run(
        "swim_ai_reflex.backend.api.main:api_app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )


def run_reflex(port: int = 3000, backend_port: int = 8000):
    """
    Run the Reflex application.

    Args:
        port: Frontend port
        backend_port: Backend port
    """
    logger.info(f"🌊 Starting Reflex frontend on port {port}")

    env = os.environ.copy()
    env["REFLEX_FRONTEND_PORT"] = str(port)
    env["REFLEX_BACKEND_PORT"] = str(backend_port)

    subprocess.run(
        [
            "reflex",
            "run",
            "--frontend-port",
            str(port),
            "--backend-port",
            str(backend_port),
        ],
        cwd=str(get_project_root()),
        env=env,
    )


async def run_hybrid(
    reflex_port: int = 3000, reflex_backend_port: int = 8000, fastapi_port: int = 8001
):
    """
    Run both Reflex and FastAPI in hybrid mode.

    This allows:
    - Reflex frontend to work as usual
    - External API access via FastAPI on a separate port

    Args:
        reflex_port: Reflex frontend port
        reflex_backend_port: Reflex backend port
        fastapi_port: FastAPI server port
    """
    import uvicorn

    logger.info("🔄 Starting HYBRID mode...")
    logger.info(f"   🌊 Reflex frontend: http://localhost:{reflex_port}")
    logger.info(f"   🔧 Reflex backend: http://localhost:{reflex_backend_port}")
    logger.info(f"   🚀 FastAPI: http://localhost:{fastapi_port}")
    logger.info(f"   📚 API docs: http://localhost:{fastapi_port}/api/docs")

    # Create uvicorn config for FastAPI
    config = uvicorn.Config(
        "swim_ai_reflex.backend.api.main:api_app",
        host="0.0.0.0",
        port=fastapi_port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    # Run FastAPI in background
    fastapi_task = asyncio.create_task(server.serve())

    # Run Reflex in subprocess
    env = os.environ.copy()
    reflex_process = subprocess.Popen(
        [
            "reflex",
            "run",
            "--frontend-port",
            str(reflex_port),
            "--backend-port",
            str(reflex_backend_port),
        ],
        cwd=str(get_project_root()),
        env=env,
    )

    # Handle shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down...")
        reflex_process.terminate()
        fastapi_task.cancel()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for either to complete
    try:
        reflex_process.wait()
    except KeyboardInterrupt:
        shutdown(None, None)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="AquaForge Server Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_server.py --mode reflex          # Run Reflex only (default)
  python run_server.py --mode api             # Run FastAPI only
  python run_server.py --mode hybrid          # Run both
  python run_server.py --mode api --port 8001 --reload  # Dev mode for API
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["reflex", "api", "hybrid"],
        default="reflex",
        help="Server mode: reflex (default), api (FastAPI only), or hybrid (both)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Primary port (3000 for reflex, 8001 for api)",
    )

    parser.add_argument(
        "--api-port", type=int, default=8001, help="FastAPI port (for hybrid mode)"
    )

    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")

    args = parser.parse_args()

    # Set default ports based on mode
    if args.port is None:
        if args.mode == "reflex":
            args.port = 3000
        elif args.mode == "api":
            args.port = 8001
        else:  # hybrid
            args.port = 3000

    logger.info(f"🎯 Mode: {args.mode.upper()}")

    if args.mode == "api":
        run_fastapi(host=args.host, port=args.port, reload=args.reload)
    elif args.mode == "reflex":
        run_reflex(port=args.port)
    elif args.mode == "hybrid":
        asyncio.run(run_hybrid(reflex_port=args.port, fastapi_port=args.api_port))


if __name__ == "__main__":
    main()
