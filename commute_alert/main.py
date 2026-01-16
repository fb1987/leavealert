import argparse
import os
import sys
import datetime as dt

from commute_alert.clock import get_now
from commute_alert.config import get_issue_number, load_config
from commute_alert.errors import CommuteAlertError
from commute_alert.github import issues
from commute_alert.logic import Decision, decide_send, should_run_today
from commute_alert.providers.google_routes import compute_route_duration

STATE_PATH = ".commute_alert_state.json"


def _bool_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Commute Alert")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default="config.yml")
    return parser.parse_args()


def _compose_message(username: str, decision: Decision, eta_minutes: int, config) -> str:
    commute = config["commute"]
    buffer = commute["buffer_minutes"]
    arrival = commute["arrival_time"]
    leave_by = decision.leave_by.strftime("%H:%M")
    return (
        f"@{username} Leave by {leave_by} to arrive {arrival}. "
        f"ETA {eta_minutes}m (buffer {buffer}m)."
    )


def main() -> int:
    args = parse_args()
    bootstrap = args.bootstrap or _bool_env(os.getenv("INPUT_BOOTSTRAP"))
    dry_run = args.dry_run or _bool_env(os.getenv("INPUT_DRY_RUN"))

    config = load_config(args.config)
    state = issues.load_local_state(STATE_PATH)

    if bootstrap:
        if get_issue_number(config, state):
            print("Issue already configured. Skipping bootstrap.")
            return 0
        issue_number = issues.bootstrap_issue(
            "Commute Alerts",
            {
                "issue_number": None,
                "last_sent_date": None,
                "last_sent_type": None,
                "last_computed_leave_by": None,
                "last_eta_seconds": None,
                "last_error": None,
                "last_run_at": None,
            },
        )
        state["issue_number"] = issue_number
        issues.save_state(issue_number, state)
        issues.save_local_state(STATE_PATH, state)
        print(f"Bootstrap complete. Issue #{issue_number} created.")
        return 0

    issue_number = get_issue_number(config, state)
    if not issue_number:
        raise CommuteAlertError(
            "Issue number missing. Run bootstrap or set notifications.issue_number."
        )

    issue_state = issues.load_state(issue_number)
    merged_state = {**state, **issue_state}

    now = get_now(config.user["timezone"])
    if not config.commute.get("enabled", True):
        print("Commute is disabled; exiting.")
        return 0

    if not should_run_today(config.commute["days"], now):
        print("Today is not an active commute day; exiting.")
        return 0

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise CommuteAlertError("GOOGLE_MAPS_API_KEY is required")

    try:
        travel_duration = compute_route_duration(config.route, api_key)
        merged_state["last_eta_seconds"] = int(travel_duration.total_seconds())
        merged_state["last_error"] = None
    except Exception as exc:  # noqa: BLE001
        merged_state["last_error"] = str(exc)
        issues.save_state(issue_number, merged_state)
        raise

    decision = decide_send(now, config.__dict__, travel_duration, merged_state)
    eta_minutes = int(travel_duration.total_seconds() / 60)

    print(f"Route ETA minutes: {eta_minutes}")
    print(f"Leave by: {decision.leave_by.isoformat()}")
    print(f"Notify at: {decision.notify_at.isoformat()}")
    print(f"Now: {now.isoformat()}")
    print(f"Decision: {decision.message}")

    if decision.send:
        comment = _compose_message(config.user["github_username"], decision, eta_minutes, config.__dict__)
        if dry_run:
            print("Dry run enabled. Would send comment:")
            print(comment)
        else:
            issues.post_comment(issue_number, comment)
            merged_state["last_sent_date"] = now.date().isoformat()
            merged_state["last_sent_type"] = decision.send_type

    merged_state["last_computed_leave_by"] = decision.leave_by.isoformat()
    merged_state["last_run_at"] = now.isoformat()
    issues.save_state(issue_number, merged_state)
    issues.save_local_state(STATE_PATH, merged_state)

    return 0


def run() -> None:
    try:
        sys.exit(main())
    except CommuteAlertError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    run()
