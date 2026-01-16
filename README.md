# Commute Alert (Template)

Daily leave-by alerts via GitHub Actions + GitHub Mobile push notifications. This repo is a template: copy it, add your Google Routes API key, and get a direct-mention alert when it’s time to leave.

## What this is
- ✅ GitHub Actions scheduler (no servers)
- ✅ Google Routes API for traffic-aware ETA
- ✅ GitHub Mobile push via direct @mention on a single Issue
- ❌ No SMS
- ❌ No minute-perfect guarantees (Actions schedule is best-effort)

## Quickstart (≈10 minutes)
1. **Use this template** to create a new repo (private recommended).
2. Add your route config in `config.yml` (see `docs/CONFIG_REFERENCE.md`).
3. Add the GitHub secret `GOOGLE_MAPS_API_KEY`.
4. Run the **Commute Alert** workflow with `bootstrap=true` to create the Issue, or set `notifications.issue_title` to reference an existing Issue by title.
5. Install **GitHub Mobile** and enable push notifications for direct mentions.

## Setup
### 1) Configure `config.yml`
Example schema is below; full reference is in `docs/CONFIG_REFERENCE.md`.

### 2) Create a Google Routes API key
Follow `docs/SETUP_GOOGLE_CLOUD.md`.

### 3) Add the secret
In your repo settings, add `GOOGLE_MAPS_API_KEY` (never commit it).

### 4) Bootstrap
Run **Actions → Commute Alert → Run workflow** with:
- `bootstrap: true`

The workflow creates a “Commute Alerts” Issue and stores the issue number in `.commute_alert_state.json`.
If you prefer, set `notifications.issue_title` (and optionally `notifications.state_issue_title`) in `config.yml` to use existing Issues instead of bootstrapping.

### 5) Enable GitHub Mobile mentions
See `docs/NOTIFICATIONS_GITHUB_MOBILE.md`.

## Scheduling & Reliability
- The workflow runs **every 5 minutes** on a UTC cron schedule (offset away from minute 0).
- **Scheduled events are best-effort**; runs can be delayed or dropped.
- Use the built-in **grace windows** and the optional **leave now** fallback.
- GitHub may **auto-disable scheduled workflows** after 60 days of repo inactivity (especially for public repos).

## Privacy & Security
- Use a **private repo**: config contains home/work addresses.
- Use **GitHub Secrets** for API keys.
- Lock your API key to the **Routes API**. IP restrictions are not reliable with GitHub-hosted runners.

## Troubleshooting
- Billing not enabled? Routes API requests will fail.
- Routes API not enabled? Enable it in GCP.
- Actions disabled after inactivity? Re-enable workflows in repo settings.

## License
MIT. See `LICENSE`.
