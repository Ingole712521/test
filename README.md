# Job contact finder + mail merge

Two-step workflow:

1. **Find jobs and HR/career emails** → Excel  
2. **Send personalized emails** from that Excel via Gmail

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your Gmail address and [App Password](https://myaccount.google.com/apppasswords) for step 2.

## Step 1 — Remote jobs with Scrapy (recommended for remote boards)

Uses **Scrapy** to crawl remote job sites, then finds each company's career / HR / info email and writes Excel.

**Boards:** Indeed, Naukri (remote), RemoteOK, Remotive, We Work Remotely, remote.co, NoDesk, Working Nomads.

```bash
python remote_job_scraper.py
```

Scrape + find emails + send mail in one command:

```bash
python remote_job_scraper.py --roles "DevOps Engineer,React Developer" --limit 30 --send --template email_template.txt
```

| Flag | Default | Description |
|------|---------|-------------|
| `--roles` | React Developer, DevOps Engineer | Comma-separated job titles |
| `--sites` | all remote boards above | Comma-separated site keys |
| `--limit` | `50` | Max companies to look up for emails |
| `--results-per-site` | `25` | Max jobs per board per role |
| `--experience-min` / `--experience-max` | `1` / `4` | Experience filter |
| `--output` | `Company_email.xlsx` | Output Excel |
| `--send` | off | Run `send_mail_merge.py` after Excel is ready |
| `--dry-run` | off | Scrape only; print jobs, skip email lookup |

Then (if you did not use `--send`):

```bash
python send_mail_merge.py --excel Company_email.xlsx --template email_template.txt
```

## Step 1 (alternate) — Search jobs and extract emails

Searches these sources (via web search, no login):

| Site key | Platform |
|----------|----------|
| `naukri` | Naukri.com |
| `indeed` | Indeed India / global |
| `linkedin` | LinkedIn Jobs |
| `glassdoor` | Glassdoor |
| `foundit` | Foundit (Monster India) |
| `reddit` | Reddit job posts |
| `remoteok` | RemoteOK |
| `remotive` | Remotive |
| `weworkremotely` | We Work Remotely |
| `remoteco` | Remote.co |

**LinkedIn AWS / DevOps only** (company, email, role columns):

```bash
python linkedin_devops_jobs.py
```

Searches LinkedIn job postings (public listings via web search), then finds HR/career emails on company sites and Google. Output: `Company_email.xlsx` with **Company Name**, **Email ID**, **Role**.

**Default run** (React + DevOps, 1–4 years experience, India, all sites above):

```bash
python find_job_contacts.py
```

Custom example:

```bash
python find_job_contacts.py --roles "React Developer,DevOps Engineer" --experience-min 1 --experience-max 4 --location India --limit 50
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--roles` | React Developer, DevOps Engineer | Comma-separated job titles |
| `--role` | — | Single role (alternative to `--roles`) |
| `--location` | `India` | Location in search |
| `--sites` | all boards listed above | Comma-separated site keys |
| `--experience-min` | `1` | Min years of experience |
| `--experience-max` | `4` | Max years of experience |
| `--limit` | `50` | Max companies to look up |
| `--output` | `Company_email.xlsx` | Output file |
| `--delay` | `1.5` | Pause between companies (seconds) |
| `--no-remote-sites` | off | Skip remote job boards |

**Excel columns:** Comapany Name, EmailID, Website, Job Title, Job URL, Career Page, Source, Location, Status.

Rows without a public email show `NO email id` (same as your existing sheet). Not every company publishes HR email on the web.

## Fill emails from your own Excel (web scraper)

If you already have a list of **company names** in Excel and need **HR / careers / contact / info** emails:

```bash
python scrape_emails_from_excel.py --excel Company_email.xlsx --only-missing
```

| Flag | Default | Description |
|------|---------|-------------|
| `--excel` | `Company_email.xlsx` | Input file (updated in place unless `--output` is set) |
| `--only-missing` | off | Skip rows that already have a valid email |
| `--limit` | all rows | Max companies to look up |
| `--delay` | `1.5` | Pause between companies (seconds) |
| `--max-emails` | `3` | Emails per company (comma-separated in one cell) |
| `--output` | — | Write to another file instead of overwriting |

Required columns: **Company Name** (or `Comapany Name`) and **Email ID** (optional **Website** column for faster lookups).

## Step 2 — Send emails (existing script)

```bash
python send_mail_merge.py --excel Company_email.xlsx --template email_template.txt
```

Dry run:

```bash
python send_mail_merge.py --excel Company_email.xlsx --template email_template.txt --dry-run
```

Template uses `{{COMPANY_NAME}}` in subject/body. See `email_template.txt`.

After each send, the script waits **3 seconds** (default) and checks Gmail via IMAP for a **Mail Delivery Subsystem** bounce for that address. If one arrives, it **deletes the bounce message** and **removes that company row** from the Excel file (company name + email). Enable **IMAP** on your Gmail account (same app password as SMTP).

| Flag | Default | Description |
|------|---------|-------------|
| `--bounce-wait` | `3` | Seconds to wait before checking for a bounce |
| `--no-bounce-check` | off | Skip bounce detection and row removal |

## Notes

- Job boards may block automated access; this tool uses search + public career pages, not logged-in scraping.
- Respect each site’s terms of use and rate limits; increase `--delay` if searches fail.
- For best results, use a specific role name and location (e.g. `"Bangalore"` instead of only `"India"`).
