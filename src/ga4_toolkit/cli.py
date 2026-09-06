from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any

from . import __version__
from .client import (
    ANALYTICS_READONLY_SCOPE,
    AnalyticsClient,
    AnalyticsError,
    config_path,
    default_service_account_path,
    flatten_report,
    normalize_property_id,
    read_config,
    resolve_property_id,
    save_default_property,
)
from .formatting import render_metadata, render_report, render_rows
from .presets import acquisition, events, overview, pages


def comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return parsed


def add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--property", help="Numeric GA4 property ID")
    parser.add_argument(
        "--format",
        choices=("table", "json", "csv"),
        default="table",
        help="Output format (default: table)",
    )


def add_date_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start", default="28daysAgo", help="Start date")
    parser.add_argument("--end", default="yesterday", help="End date")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4", description="Read-only Google Analytics 4 CLI"
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_parser = subparsers.add_parser(
        "auth", help="Check credentials or create user ADC with a custom OAuth client"
    )
    auth_parser.add_argument(
        "--launch-browser",
        action="store_true",
        help="Allow gcloud to launch the default browser",
    )
    auth_parser.add_argument(
        "--client-id-file",
        help="Desktop OAuth client JSON required for user ADC with Analytics scope",
    )

    subparsers.add_parser("doctor", help="Check credentials and Analytics access")

    properties_parser = subparsers.add_parser(
        "properties", help="List accessible GA4 properties"
    )
    properties_parser.add_argument(
        "--format", choices=("table", "json", "csv"), default="table"
    )

    use_parser = subparsers.add_parser("use", help="Save the default GA4 property")
    use_parser.add_argument("property_id")

    subparsers.add_parser("config", help="Show non-secret toolkit configuration")

    for name, help_text in (
        ("overview", "Daily overview"),
        ("pages", "Top pages"),
        ("acquisition", "Acquisition channels and sources"),
        ("events", "Top events"),
    ):
        command_parser = subparsers.add_parser(name, help=help_text)
        add_output_options(command_parser)
        add_date_options(command_parser)
        if name != "overview":
            command_parser.add_argument("--limit", type=int, default=25)

    realtime_parser = subparsers.add_parser("realtime", help="Realtime report")
    add_output_options(realtime_parser)
    realtime_parser.add_argument("--dimensions", type=comma_list, default=["country"])
    realtime_parser.add_argument(
        "--metrics", type=comma_list, default=["activeUsers", "eventCount"]
    )
    realtime_parser.add_argument("--limit", type=int, default=100)
    realtime_parser.add_argument("--order-by")
    realtime_parser.add_argument("--ascending", action="store_true")

    report_parser = subparsers.add_parser("report", help="Custom historical report")
    add_output_options(report_parser)
    add_date_options(report_parser)
    report_parser.add_argument("--dimensions", type=comma_list, required=True)
    report_parser.add_argument("--metrics", type=comma_list, required=True)
    report_parser.add_argument("--limit", type=int, default=100)
    report_parser.add_argument("--order-by")
    report_parser.add_argument("--ascending", action="store_true")
    report_parser.add_argument("--dimension-filter-json", type=json_object)
    report_parser.add_argument("--metric-filter-json", type=json_object)

    metadata_parser = subparsers.add_parser(
        "metadata", help="List available dimensions and metrics"
    )
    add_output_options(metadata_parser)
    metadata_parser.add_argument("--search")
    return parser


def run_auth(launch_browser: bool, client_id_file: str | None) -> int:
    service_account_file = default_service_account_path()
    if service_account_file.is_file() and not client_id_file:
        print(f"Dedicated service-account credentials: {service_account_file}")
        print("Authentication is already configured.")
        return 0
    if not client_id_file:
        raise AnalyticsError(
            "No dedicated service-account credentials were found. Google requires a custom "
            "Desktop OAuth client for user ADC with the Analytics scope; pass its JSON file "
            "with --client-id-file."
        )
    gcloud = shutil.which("gcloud")
    if not gcloud:
        raise AnalyticsError(
            "gcloud is not installed. Install the Google Cloud CLI, then run `ga4 auth` again; "
            "or use GOOGLE_APPLICATION_CREDENTIALS with a read-only service account."
        )
    command = [
        gcloud,
        "auth",
        "application-default",
        "login",
        f"--scopes=https://www.googleapis.com/auth/cloud-platform,{ANALYTICS_READONLY_SCOPE}",
        f"--client-id-file={client_id_file}",
    ]
    if not launch_browser:
        command.append("--no-launch-browser")
    return subprocess.run(command, check=False).returncode


def print_report(payload: dict[str, Any], output_format: str) -> None:
    for warning in flatten_report(payload)["warnings"]:
        print(f"ga4: warning: {warning}", file=sys.stderr)
    print(render_report(payload, output_format))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "auth":
            return run_auth(args.launch_browser, args.client_id_file)

        client = AnalyticsClient()
        if args.command == "doctor":
            properties = client.list_properties()
            print(f"Credentials: OK\nAccessible GA4 properties: {len(properties)}")
            if read_config().get("default_property_id"):
                print(f"Default property: {read_config()['default_property_id']}")
            return 0
        if args.command == "properties":
            print(render_rows(client.list_properties(), args.format))
            return 0
        if args.command == "use":
            path = save_default_property(args.property_id)
            print(f"Default property saved in {path}")
            return 0
        if args.command == "config":
            print(
                json.dumps(
                    {"path": str(config_path()), **read_config()},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.property is None:
            args.property = resolve_property_id()
            print(
                f"ga4: using configured property {args.property}; "
                "pass --property to select it explicitly.",
                file=sys.stderr,
            )
        else:
            args.property = normalize_property_id(args.property)
        if args.command == "overview":
            payload = overview(
                client,
                property_id=args.property,
                start_date=args.start,
                end_date=args.end,
            )
            print_report(payload, args.format)
            return 0
        if args.command in {"pages", "acquisition", "events"}:
            preset = {"pages": pages, "acquisition": acquisition, "events": events}[
                args.command
            ]
            payload = preset(
                client,
                property_id=args.property,
                start_date=args.start,
                end_date=args.end,
                limit=args.limit,
            )
            print_report(payload, args.format)
            return 0
        if args.command == "realtime":
            payload = client.run_realtime_report(
                property_id=args.property,
                dimensions=args.dimensions,
                metrics=args.metrics,
                limit=args.limit,
                order_by_metric=args.order_by,
                descending=not args.ascending,
            )
            print_report(payload, args.format)
            return 0
        if args.command == "report":
            payload = client.run_report(
                property_id=args.property,
                dimensions=args.dimensions,
                metrics=args.metrics,
                start_date=args.start,
                end_date=args.end,
                limit=args.limit,
                dimension_filter=args.dimension_filter_json,
                metric_filter=args.metric_filter_json,
                order_by_metric=args.order_by,
                descending=not args.ascending,
            )
            print_report(payload, args.format)
            return 0
        if args.command == "metadata":
            payload = client.get_metadata(
                property_id=args.property, search=args.search
            )
            print(render_metadata(payload, args.format))
            return 0
    except AnalyticsError as exc:
        print(f"ga4: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
