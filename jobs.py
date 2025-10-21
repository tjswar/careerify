# jobs.py
import requests
from bs4 import BeautifulSoup

def fetch_job_descriptions(job_title: str, location: str = "United States", limit: int = 10) -> list[str]:
    """
    Try Indeed first. If it returns nothing, caller can optionally try RemoteOK fallback.
    Returns a list of short text snippets (job descriptions).
    """
    q = job_title.replace(" ", "+")
    url = f"https://www.indeed.com/jobs?q={q}&l={location}&limit={min(limit, 20)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = []
        for div in soup.select("div.job_seen_beacon"):
            desc = div.select_one("div.job-snippet")
            if desc:
                text = desc.get_text(" ").strip()
                if text:
                    jobs.append(text)
        return jobs[:limit]
    except Exception:
        return []


def fetch_remoteok_fallback(job_title: str, limit: int = 10) -> list[str]:
    """RemoteOK public API fallback; returns short text snippets."""
    try:
        r = requests.get("https://remoteok.com/api", timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        data = r.json()
        results = []
        jt = job_title.lower()
        for item in data:
            if not isinstance(item, dict):
                continue
            title = (item.get("position") or item.get("title") or "").lower()
            if jt in title:
                html = (item.get("description") or "")[:1500]
                soup = BeautifulSoup(html, "html.parser")
                snippet = soup.get_text(" ").strip()
                if snippet:
                    results.append(snippet)
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []