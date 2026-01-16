# Config Reference

`config.yml` schema (v1):

```yaml
version: 1

user:
  github_username: "yourhandle"
  timezone: "America/Toronto"

commute:
  name: "Work"
  enabled: true
  days: ["mon", "tue", "wed", "thu", "fri"]
  arrival_time: "08:30"
  buffer_minutes: 10
  lead_minutes: 15
  estimated_duration_minutes: 35

route:
  mode: "DRIVE"
  origin:
    address: "123 Home St, City, Province"
    # or:
    # lat: 43.6532
    # lng: -79.3832
  destination:
    address: "456 Office Ave, City, Province"
  # waypoints: []

notifications:
  channel: "github_mention"
  issue_number: null
  issue_title: "alert"
  state_issue_number: null
  state_issue_title: "state"
  grace_minutes: 10
  leave_grace_minutes: 10
  quiet_hours:
    enabled: false
    start: "22:00"
    end: "06:00"
```

## Notes
- `issue_number` can be null before bootstrap. The bootstrap workflow creates the Issue and stores the number in `.commute_alert_state.json`.
- `issue_title` lets you reference an existing Issue by title instead of bootstrapping a new one.
- `state_issue_number`/`state_issue_title` optionally store state in a separate Issue body. If omitted, state is stored on the alert Issue.
- `days` must be lowercase three-letter abbreviations.
