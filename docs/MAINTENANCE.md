# Maintenance guide

## Portal user accounts

See [USER_MANAGEMENT.md](USER_MANAGEMENT.md) for:

- Creating faculty accounts and welcome emails
- Deactivate / activate (temporary login block)
- Remove profile (anonymize account, keep CO-PO data, free email for re-registration)
- Forgot password (SMTP temporary password)

Ensure `SMTP_ENABLED=true` and Gmail/app-password settings in `backend/.env` for email features.

---

## Publications module

### Adding a New Faculty Member

1. Add their row to `faculty_master.csv` (include `scholar_id` from their Google Scholar profile URL).
2. Admin → Faculty → Import CSV → upload updated CSV.
3. System inserts the new faculty row automatically.
4. Admin → Publications → Sync All Publications.
5. Sync detects 0 publications for new faculty and fetches their full history from SerpAPI.

## Faculty Member Leaves

1. Set their `leave_year` in `faculty_master.csv`.
2. Re-upload CSV via Admin → Faculty → Import CSV.
3. System sets `is_active=FALSE` and `leave_year` — future syncs still process them for gap-fill but tenure filter limits new inserts.
4. Their existing publications remain in the portal unchanged.
5. They move automatically to the "Former Faculty" tab in the Faculty Directory.

## Monthly Sync (on a hosted server)

1. Set `ENABLE_SCHEDULER=true` in `backend/.env`, restart backend.
2. APScheduler fires on the 1st of each month automatically.

## Monthly Sync (running locally)

1. Keep `ENABLE_SCHEDULER=false`.
2. Each month: Admin → Publications → Sync All Publications.
3. Only new publications since last sync are inserted — no duplicates, no re-scraping.

## SerpAPI Usage

- Free tier: 250 searches/month.
- 27 faculty × 1 search per sync = 27 searches — well within free tier.
- Check usage at [serpapi.com/dashboard](https://serpapi.com/dashboard).
- Update `SERP_API_KEY` in `backend/.env` if the key changes.

## Gap-Fill Script (CLI)

```bash
cd backend
python scripts/scrape_gap_fill.py
```

Processes faculty IDs 1–27 in ascending order with a 2-second delay between each.
