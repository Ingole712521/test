from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Domains/prefixes that are rarely useful for job outreach
BLOCKED_LOCAL = {
    "noreply",
    "no-reply",
    "donotreply",
    "mailer-daemon",
    "postmaster",
    "webmaster",
    "support",
    "help",
    "info",
    "newsletter",
    "marketing",
    "sales",
    "billing",
    "privacy",
    "legal",
    "abuse",
    "dmarc",
    "sentry",
}

BLOCKED_DOMAINS = {
    "example.com",
    "email.com",
    "domain.com",
    "wixpress.com",
    "sentry.io",
    "schema.org",
    "googleusercontent.com",
    "facebook.com",
    "twitter.com",
    "linkedin.com",
    "instagram.com",
    "youtube.com",
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "internshala.com",
    "naukri.com",
    "indeed.com",
    "glassdoor.com",
    "cutshort.io",
    "shine.com",
    "timesjobs.com",
    "monster.com",
    "foundit.in",
    "wellfound.com",
}

PREFERRED_LOCAL = (
    "hr",
    "careers",
    "career",
    "jobs",
    "job",
    "recruit",
    "recruitment",
    "talent",
    "hiring",
    "people",
    "humanresources",
    "human.resources",
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


def normalize_email(raw: str) -> str | None:
    e = raw.strip().rstrip(".,;)")
    e = re.sub(r"(Role|Email|Contact|Phone|Apply)$", "", e, flags=re.I)
    # Fix glued text like name@domain.comwww.other.com
    if "@" in e:
        local, _, rest = e.partition("@")
        domain = rest
        for sep in ("www.", "http", "https", ".com", ".in", ".org", ".net"):
            idx = domain.lower().find(sep)
            if idx > 0 and not domain.lower().startswith(sep):
                # keep only first domain segment if duplicate TLD pattern
                m = re.match(r"^([a-z0-9.-]+\.[a-z]{2,})", domain, re.I)
                if m:
                    domain = m.group(1)
                    break
        e = f"{local}@{domain}"
    if not EMAIL_RE.fullmatch(e):
        return None
    local, _, domain = e.partition("@")
    domain_l = domain.lower()
    local_l = local.lower()
    if len(domain_l) > 80 or len(local_l) > 64:
        return None
    if domain_l in BLOCKED_DOMAINS:
        return None
    if any(domain_l.endswith("." + d) or domain_l == d for d in BLOCKED_DOMAINS):
        return None
    if local_l in BLOCKED_LOCAL or any(local_l.startswith(p + ".") for p in BLOCKED_LOCAL):
        return None
    if local_l.endswith((".png", ".jpg", ".gif", ".svg", ".webp")):
        return None
    return e


def score_email(email: str) -> int:
    local = email.split("@", 1)[0].lower()
    score = 0
    for i, pref in enumerate(PREFERRED_LOCAL):
        if pref in local:
            score += 100 - i
    if "@" in email and len(local) < 30:
        score += 5
    return score


def extract_emails_from_text(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for m in EMAIL_RE.findall(text):
        e = normalize_email(m)
        if e and e.lower() not in seen:
            seen.add(e.lower())
            found.append(e)
    found.sort(key=score_email, reverse=True)
    return found


def fetch_page_text(url: str, timeout: int = 12) -> tuple[str, str | None]:
    """Return (html_or_text, error)."""
    try:
        resp = _session().get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            return "", f"HTTP {resp.status_code}"
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype.lower() and "text" not in ctype.lower():
            return "", "non-html response"
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text("\n", strip=True) + "\n" + str(soup), None
    except requests.RequestException as exc:
        return "", str(exc)


def extract_emails_from_url(url: str) -> list[str]:
    html, err = fetch_page_text(url)
    if err:
        return []
    emails = extract_emails_from_text(html)
    # mailto: links
    try:
        resp = _session().get(url, timeout=12, allow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select('a[href^="mailto:"]'):
            href = a.get("href", "")
            addr = href.split("mailto:", 1)[-1].split("?", 1)[0].strip()
            e = normalize_email(addr)
            if e and e not in emails:
                emails.append(e)
    except requests.RequestException:
        pass
    emails.sort(key=score_email, reverse=True)
    return emails


def same_domain(url_a: str, url_b: str) -> bool:
    try:
        return urlparse(url_a).netloc.replace("www.", "") == urlparse(url_b).netloc.replace(
            "www.", ""
        )
    except Exception:
        return False


def discover_career_links(base_url: str, html: str) -> list[str]:
    """Find likely career/contact links on a company page."""
    soup = BeautifulSoup(html, "lxml")
    keywords = (
        "career",
        "careers",
        "jobs",
        "job",
        "join",
        "hiring",
        "work-with",
        "workwith",
        "vacanc",
        "recruit",
        "contact",
    )
    out: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text() or "").lower()
        href_l = href.lower()
        if not any(k in href_l or k in text for k in keywords):
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        seen.add(full)
        out.append(full)
    return out[:8]
