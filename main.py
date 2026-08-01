import argparse
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import WarrantyEngine
from interfaces.cli import run_cli_mode
from interfaces.web import run_web_mode
from core.diagnostics import build_diagnostic_report, print_diagnostic_report
from core.printers.setup_service import configure_printer_binding
from core.printers.tsc_connector import TSCPrinterConnector


def launch_https_tunnel(port: int, timeout_seconds: float = 20.0):
    """Launch localtunnel and return its process and verified HTTPS URL."""
    tunnel_process = subprocess.Popen(
        ["npx", "-y", "localtunnel@2.0.2", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines: queue.Queue[str] = queue.Queue()

    def read_output() -> None:
        if tunnel_process.stdout is None:
            return
        for line in tunnel_process.stdout:
            output_lines.put(line)

    threading.Thread(target=read_output, daemon=True).start()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            line = output_lines.get(
                timeout=max(0.0, min(0.25, deadline - time.monotonic()))
            )
        except queue.Empty:
            if tunnel_process.poll() is not None:
                break
            continue
        print(line, end="")
        if "your url is:" not in line.lower():
            continue
        public_url = line.split("is:", 1)[-1].strip()
        if urllib.parse.urlsplit(public_url).scheme.lower() == "https":
            return tunnel_process, public_url
        break

    tunnel_process.terminate()
    try:
        tunnel_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        tunnel_process.kill()
    raise RuntimeError(
        "Could not establish a verified HTTPS tunnel. "
        "Phone camera mode was not started."
    )


def main():
    parser = argparse.ArgumentParser(description="Universal Warranty Lookup & Label Printer Application")
    parser.add_argument("--mode", choices=["cli", "web"], default="cli", help="Interface mode to run (cli or web). Default: cli")
    parser.add_argument("--port", type=int, default=9191, help="Port to run web server on when in web mode. Default: 9191")
    parser.add_argument(
        "--printer",
        choices=["file", "tsc"],
        default="tsc",
        help="CLI output connector. Defaults to the validated TSC MB341; use --printer file to disable physical printing.",
    )
    parser.add_argument("--tunnel", action="store_true", help="Launch a public HTTPS tunnel for phone camera access over 4G/5G or isolated workplace Wi-Fi.")
    parser.add_argument("--public-url", type=str, default=None, help="Explicit public HTTPS URL for phone QR pairing.")
    parser.add_argument("--update-engines", action="store_true", help="Download/update community open-source warranty engines from GitHub.")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run read-only platform, browser, path, profile, and printer checks.",
    )
    parser.add_argument(
        "--setup-printer",
        action="store_true",
        help="Select and save one explicitly validated USB TSC MB341 queue.",
    )


    args = parser.parse_args()

    if args.diagnose:
        print_diagnostic_report(build_diagnostic_report())
        return

    if args.setup_printer:
        engine = WarrantyEngine()
        connector = engine.connectors.get("tsc")
        if not isinstance(connector, TSCPrinterConnector):
            print("TSC connector is unavailable on this platform.", file=sys.stderr)
            sys.exit(1)
        configured = configure_printer_binding(connector)
        sys.exit(0 if configured is not None else 1)

    if args.update_engines:
        engine = WarrantyEngine()
        engine.update_github_engines()
        sys.exit(0)

    if args.mode == "web":
        pub_url = args.public_url
        tunnel_proc = None
        if pub_url and urllib.parse.urlsplit(pub_url).scheme.lower() != "https":
            parser.error("--public-url must use HTTPS for phone camera access")
        if args.tunnel and not pub_url:
            print(f"\n[TUNNEL] Launching public HTTPS tunnel on port {args.port}...")
            tunnel_proc, pub_url = launch_https_tunnel(args.port)
            print(f"[TUNNEL READY] Public URL: {pub_url}\n")

        try:
            run_web_mode(port=args.port, public_url=pub_url)
        finally:
            if tunnel_proc:
                tunnel_proc.terminate()

    else:
        run_cli_mode(initial_connector=args.printer)


if __name__ == "__main__":
    main()
