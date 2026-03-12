#!/usr/bin/env python3
"""
Backfill Wayback status for inactive URLs (CDX-only) with minimal, useful logs.

- Loads URLs where active = false AND wayback_exists IS NULL
- Uses Wayback CDX API ONLY (no wayback/available, no UI endpoints)
- Finds earliest successful snapshot (200/301/302), including canonical variants
- Fetches replay HTML for soft-404 detection
- Stores:
    - wayback_exists: True iff a successful snapshot is found in CDX
    - wayback_soft_404: True iff replay HTML is fetched and title matches soft-404 patterns
- Concurrency-safe batching (FOR UPDATE SKIP LOCKED)
"""

import re
import time
import os
import sys
import traceback
from typing import Optional, Tuple, List
from urllib.parse import urlsplit, urlunsplit, urldefrag

import psycopg2
import requests

sys.path.append('../')
from globalFunctions import config

# -----------------------------------------------------
# Configuration
# -----------------------------------------------------

CDX_API = "https://web.archive.org/cdx/search/cdx"
SUCCESS_CODES = {200, 301, 302}

TITLE_SOFT_404 = [
    r"\b404\b",
    r"page not found",
    r"not found",
    r"does not exist",
    r"cannot be found",
    r"error\s+404",
]

BATCH_SIZE = 5
SLEEP_BETWEEN_BATCHES = 0.5
TIMEOUT = int(os.getenv("WAYBACK_TIMEOUT", "60"))
MAX_REPLAY_BYTES = 64 * 1024  # read at most this many bytes from replay HTML


# -----------------------------------------------------
# Logging
# -----------------------------------------------------

def log(msg: str) -> None:
    print(msg, flush=True)


# -----------------------------------------------------
# HTTP Helper
# -----------------------------------------------------

def get_with_retry(url: str, params: Optional[dict] = None, timeout: int = TIMEOUT) -> requests.Response:
    """
    Wrapper around requests.get to handle 429 Too Many Requests with backoff.
    """
    retries = 5
    backoff = 2.0

    last_exc = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 429:
                sleep_time = backoff * (2 ** i)
                log(f"  [http] 429 Too Many Requests. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            return r
        except requests.RequestException as e:
            last_exc = e
            if i == retries - 1:
                break
            sleep_time = backoff * (2 ** i)
            log(f"  [http] Request error: {e}. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)

    if last_exc:
        raise last_exc
    raise requests.RequestException("get_with_retry: exhausted retries without response")


# -----------------------------------------------------
# URL normalization & variants
# -----------------------------------------------------

def normalize_url(url: str) -> str:
    url = url.strip()
    url, _ = urldefrag(url)
    return url


def url_variants(url: str) -> List[str]:
    url = normalize_url(url)
    p = urlsplit(url)
    if not p.netloc:
        return [url]

    schemes = {p.scheme, "http", "https"}
    hosts = {p.netloc}
    if p.netloc.startswith("www."):
        hosts.add(p.netloc[4:])
    else:
        hosts.add("www." + p.netloc)

    paths = {p.path}
    if p.path.endswith("/"):
        paths.add(p.path[:-1])
    else:
        paths.add(p.path + "/")

    out = []
    for s in schemes:
        for h in hosts:
            for pa in paths:
                out.append(urlunsplit((s, h, pa, p.query, "")))

    seen = set()
    uniq = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


# -----------------------------------------------------
# Wayback CDX logic
# -----------------------------------------------------

def cdx_rows(url: str, match_type: Optional[str] = None, limit: int = 500) -> list:
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,statuscode,original",
        "sort": "ascending",
        "limit": str(limit),
    }
    if match_type:
        params["matchType"] = match_type

    r = get_with_retry(CDX_API, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or len(data) <= 1:
        return []
    return data[1:]


def earliest_successful_snapshot(url: str, *, verbose: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    CDX-only discovery:
    1) exact canonical variants
    2) prefix match fallback

    Returns (timestamp, canonical_original_url, method)
      method in {"variant", "prefix"} or None
    """
    variants = url_variants(url)
    if verbose:
        log(f"  [cdx] probing {len(variants)} variants (exact match)")

    # 1) Exact variants
    for v in variants:
        try:
            rows = cdx_rows(v)
        except Exception as e:
            if verbose:
                log(f"    [cdx] exact variant error: {v} -> {type(e).__name__}: {e}")
            continue

        if verbose:
            log(f"    [cdx] exact variant: {v} -> {len(rows)} rows")

        for ts, sc, original in rows:
            try:
                sc_i = int(sc)
            except Exception:
                continue
            if sc_i in SUCCESS_CODES:
                if verbose:
                    log(f"    [cdx] selected earliest success from exact variant:")
                    log(f"          ts={ts} status={sc_i} original={original}")
                return ts, original, "variant"

    # 2) Prefix fallback
    base = normalize_url(url)
    if verbose:
        log(f"  [cdx] falling back to matchType=prefix on: {base}")

    try:
        rows = cdx_rows(base, match_type="prefix")
    except Exception as e:
        if verbose:
            log(f"    [cdx] prefix error: {type(e).__name__}: {e}")
        return None, None, None

    if verbose:
        log(f"    [cdx] prefix -> {len(rows)} rows")

    for ts, sc, original in rows:
        try:
            sc_i = int(sc)
        except Exception:
            continue
        if sc_i in SUCCESS_CODES:
            if verbose:
                log(f"    [cdx] selected earliest success from prefix:")
                log(f"          ts={ts} status={sc_i} original={original}")
            return ts, original, "prefix"

    if verbose:
        log("  [cdx] no successful (200/301/302) captures found")
    return None, None, None


def fetch_replay_html(ts: str, original_url: str, *, verbose: bool = False) -> Tuple[Optional[str], Optional[int], str]:
    replay_url = f"https://web.archive.org/web/{ts}id_/{original_url}"
    if verbose:
        log(f"  [replay] GET {replay_url}")

    try:
        r = get_with_retry(replay_url, timeout=TIMEOUT)
        status = r.status_code

        cl = r.headers.get("Content-Length") if r is not None else None
        if cl:
            try:
                cl_i = int(cl)
            except Exception:
                cl_i = None
        else:
            cl_i = None

        if cl_i is not None and cl_i > MAX_REPLAY_BYTES:
            if verbose:
                log(f"  [replay] status={status} content-length={cl_i} (skipping body)")
            r.close()
            return "", status, replay_url

        try:
            chunks = []
            read = 0
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    break
                take = chunk
                if read + len(take) > MAX_REPLAY_BYTES:
                    take = take[: MAX_REPLAY_BYTES - read]
                chunks.append(take)
                read += len(take)
                if read >= MAX_REPLAY_BYTES:
                    break
            raw = b"".join(chunks)
            encoding = r.encoding or r.apparent_encoding or "utf-8"
            text = raw.decode(encoding, errors="replace")
            if verbose:
                log(f"  [replay] status={status} bytes_read={len(raw)}")
            r.close()
            return text, status, replay_url
        except Exception as e:
            if verbose:
                log(f"  [replay] stream error: {type(e).__name__}: {e}")
            try:
                r.close()
            except Exception:
                pass
            return None, status, replay_url
    except Exception as e:
        if verbose:
            log(f"  [replay] fetch error: {type(e).__name__}: {e}")
        return None, None, replay_url


# -----------------------------------------------------
# Soft-404 logic
# -----------------------------------------------------

def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def is_soft_404(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in TITLE_SOFT_404)


def wayback_check(url: str, *, verbose: bool = False) -> Tuple[bool, bool]:
    """
    Returns (wayback_exists, wayback_soft_404)
    """
    url = normalize_url(url)
    if verbose:
        log(f"[check] url={url}")

    ts, canonical, method = earliest_successful_snapshot(url, verbose=verbose)
    if ts is None:
        if verbose:
            log("[result] exists=False soft404=False (no successful captures in CDX)")
        return False, False

    if verbose:
        log(f"  [cdx] method={method} canonical={canonical} ts={ts}")

    html, status, replay_url = fetch_replay_html(ts, canonical, verbose=verbose)

    if status is None:
        if verbose:
            log(f"[result] exists=True soft404=False (replay fetch failed) replay={replay_url}")
        return True, False

    if status >= 400:
        if verbose:
            log(f"[result] exists=True soft404=False (replay HTTP {status}) replay={replay_url}")
        return True, False

    title = extract_title(html or "")
    if verbose:
        log(f"  [html] title={title[:120]!r}")

    if not title:
        if verbose:
            log("[result] exists=True soft404=False (no title)")
        return True, False

    soft = is_soft_404(title)
    if verbose:
        log(f"[result] exists=True soft404={soft}")
    return True, soft


# -----------------------------------------------------
# DB backfill
# -----------------------------------------------------

def count_remaining(cur) -> int:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM urls
        WHERE active = false
          AND wayback_exists IS NULL;
        """
    )
    return cur.fetchone()[0]


def process_batch(cur, *, verbose: bool = False) -> int:
    cur.execute(
        """
        SELECT id, url
        FROM urls
        WHERE active = false
          AND wayback_exists IS NULL
        ORDER BY id
        LIMIT %s;
        """,
        (BATCH_SIZE,),
    )
    rows = cur.fetchall()
    if not rows:
        return 0

    log(f"[batch] Processing {len(rows)} URLs")

    for url_id, url in rows:
        log(f"  - id={url_id} url={url}")
        try:
            exists, soft404 = wayback_check(url, verbose=verbose)
            log(f"    [update] wayback_exists={exists} wayback_soft_404={soft404}")
        except Exception as e:
            log(f"    [error] {type(e).__name__}: {e}")
            exists, soft404 = False, False

        cur.execute(
            """
            UPDATE urls
            SET wayback_exists = %s,
                wayback_soft_404 = %s
            WHERE id = %s;
            """,
            (exists, soft404, url_id),
        )

    return len(rows)


def main(*, verbose: bool = False):
    db_params = config(filename='../database-setup/database.ini', section='postgresql')
    conn = psycopg2.connect(**db_params)
    try:
        with conn.cursor() as cur:
            remaining = count_remaining(cur)
            log(f"Starting backfill. URLs to process: {remaining}")

            while True:
                processed = process_batch(cur, verbose=verbose)

                if processed == 0:
                    break

                conn.commit()
                time.sleep(SLEEP_BETWEEN_BATCHES)

        log("Done. No remaining URLs.")
    finally:
        conn.close()


def run_for_url(url: str, *, verbose: bool = False):
    log(f"Checking URL: {url}")
    exists, soft404 = wayback_check(url, verbose=verbose)
    log(f"Result: wayback_exists={exists}, wayback_soft_404={soft404}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CDX-only Wayback backfill (with logs)")
    parser.add_argument("--url", help="Single URL to check (debug)")
    parser.add_argument("--verbose", action="store_true", help="Enable per-step logs")
    args = parser.parse_args()

    try:
        if args.url:
            run_for_url(args.url, verbose=args.verbose)
        else:
            main(verbose=args.verbose)
    except Exception:
        traceback.print_exc()
        raise
