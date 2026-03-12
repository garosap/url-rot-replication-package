#!/usr/bin/env python3
"""
Persistent URL & URL-shortener analysis
========================================
Connects to the database and reports:

  1. URL shorteners  — absolute count, % of total, activity %
  2. Persistent URLs — overall count, % of total, activity %
  3. Per-category breakdown:
       DOI resolvers, Handle System, ARK, PURL, w3id,
       Perma.cc, Internet Archive snapshots, Zenodo records,
       Software Heritage (SWHID gateway)

Absolute counts + activity % are shown for every category.
Results are printed to the console.
"""

import re
import sys
import psycopg2
import pandas as pd
from urllib.parse import urlparse

sys.path.append('../')
from globalFunctions import config

# ─── Connection ───────────────────────────────────────────────────────────────

params = config(filename='../database-setup/database.ini', section='postgresql')

conn = psycopg2.connect(**params)
cur  = conn.cursor()
cur.execute("SELECT id, url, active FROM urls")
cols = [d[0] for d in cur.description]
df   = pd.DataFrame(cur.fetchall(), columns=cols)

# Fetch per-year URL counts (via paper_urls → papers)
cur.execute("""
    SELECT p.year, u.id AS url_id, u.url
    FROM urls u
    JOIN paper_urls pu ON pu.url_id = u.id
    JOIN papers p      ON p.id = pu.paper_id
    WHERE p.year IS NOT NULL
""")
year_cols   = [d[0] for d in cur.description]
year_url_df = pd.DataFrame(cur.fetchall(), columns=year_cols)

cur.close()
conn.close()

df['is_active'] = df['active'].fillna(False).astype(bool)
total = len(df)

print(f"Total URLs in database : {total:,}")
print()


# ─── Helper ──────────────────────────────────────────────────────────────────

def norm_host(url: str) -> str:
    """Return lowercase, www-stripped hostname."""
    try:
        h = urlparse(url).netloc.lower().strip()
        if h.startswith("www."):
            h = h[4:]
        return h
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  URL SHORTENERS
# ═══════════════════════════════════════════════════════════════════════════════

SHORTENER_DOMAINS = {
    "bit.ly", "bitly.com",
    "tinyurl.com",
    "t.co",
    "ow.ly",
    "buff.ly",
    "goo.gl",
    "is.gd",
    "short.io",
    "rebrand.ly",
    "bl.ink",
    "tiny.cc",
    "cutt.ly",
    "shorturl.at",
    "rb.gy",
    "lnkd.in",
    "fb.me",
    "adf.ly",
    "clck.ru",
    "tr.im",
    "su.pr",
    "snipurl.com",
    "snurl.com",
    "cli.gs",
    "url4.eu",
    "twurl.nl",
    "u.to",
    "v.gd",
    "x.co",
    "qr.net",
    "1url.com",
    "short.link",
    "zpr.io",
    "prettylnk.com",
}

df['host']    = df['url'].apply(norm_host)
mask_short    = df['host'].isin(SHORTENER_DOMAINS)
short_df      = df[mask_short]

short_total   = len(short_df)
short_pct     = short_total / total * 100 if total else 0
short_active  = int(short_df['is_active'].sum())
short_act_pct = short_active / short_total * 100 if short_total else 0

print("=" * 65)
print("URL SHORTENERS")
print(f"  Count          : {short_total:,}")
print(f"  % of total     : {short_pct:.2f}%")
print(f"  Active count   : {short_active:,}")
print(f"  Activity %     : {short_act_pct:.2f}%")
print()

if short_total > 0:
    short_by_domain = (
        short_df.groupby('host')
        .agg(count=('id', 'count'), active=('is_active', 'sum'))
        .assign(activity_pct=lambda x: (x['active'] / x['count'] * 100).round(2))
        .sort_values('count', ascending=False)
        .reset_index()
        .rename(columns={"host": "domain"})
    )
    print("  Per-domain breakdown:")
    print(short_by_domain.to_markdown(index=False))
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  PERSISTENT URLs
# ═══════════════════════════════════════════════════════════════════════════════

_ARK_PATH_RE   = re.compile(r"/ark:/\d{4,}", re.IGNORECASE)
_ARK_HOSTS     = {"n2t.net", "ark.cdlib.org"}
_SWHID_PATH_RE = re.compile(r"/swh:\d:", re.IGNORECASE)


def is_doi(url: str) -> bool:
    """doi.org or dx.doi.org resolver."""
    return norm_host(url) in {"doi.org", "dx.doi.org"}


def is_handle(url: str) -> bool:
    """hdl.handle.net Handle System resolver."""
    return norm_host(url) == "hdl.handle.net"


def is_ark(url: str) -> bool:
    """
    ARK identifier: dedicated ARK resolvers (n2t.net, ark.cdlib.org)
    OR any URL with /ark:/<naan> in the path.
    """
    h = norm_host(url)
    if h in _ARK_HOSTS:
        return True
    try:
        return bool(_ARK_PATH_RE.search(urlparse(url).path))
    except Exception:
        return False


def is_purl(url: str) -> bool:
    """Classic PURL — purl.org redirect namespace."""
    return norm_host(url) == "purl.org"


def is_w3id(url: str) -> bool:
    """w3id.org community-run persistent redirect namespace."""
    return norm_host(url) == "w3id.org"


def is_permacc(url: str) -> bool:
    """Perma.cc archived snapshot."""
    return norm_host(url) == "perma.cc"


def is_internet_archive(url: str) -> bool:
    """Internet Archive Wayback snapshot: web.archive.org/web/<ts>/..."""
    if norm_host(url) != "web.archive.org":
        return False
    try:
        return urlparse(url).path.startswith("/web/")
    except Exception:
        return False


def is_zenodo_record(url: str) -> bool:
    """Zenodo record URL: zenodo.org/record/<id>."""
    if norm_host(url) != "zenodo.org":
        return False
    try:
        return urlparse(url).path.startswith("/record/")
    except Exception:
        return False


def is_software_heritage(url: str) -> bool:
    """Software Heritage SWHID gateway: archive.softwareheritage.org/swh:1:..."""
    if norm_host(url) != "archive.softwareheritage.org":
        return False
    try:
        return bool(_SWHID_PATH_RE.search(urlparse(url).path))
    except Exception:
        return False


PERSISTENT_CATEGORIES = [
    ("DOI resolver",      is_doi),
    ("Handle System",     is_handle),
    ("ARK",               is_ark),
    ("PURL",              is_purl),
    ("w3id",              is_w3id),
    ("Perma.cc",          is_permacc),
    ("Internet Archive",  is_internet_archive),
    ("Zenodo record",     is_zenodo_record),
    ("Software Heritage", is_software_heritage),
]

# ─── Apply category flags ────────────────────────────────────────────────────

for cat_name, cat_fn in PERSISTENT_CATEGORIES:
    df[f"_pers_{cat_name}"] = df['url'].apply(cat_fn)

pers_cols      = [f"_pers_{c}" for c, _ in PERSISTENT_CATEGORIES]
df['is_persistent'] = df[pers_cols].any(axis=1)

pers_df        = df[df['is_persistent']]
pers_total     = len(pers_df)
pers_pct       = pers_total / total * 100 if total else 0
pers_active    = int(pers_df['is_active'].sum())
pers_act_pct   = pers_active / pers_total * 100 if pers_total else 0

print("=" * 65)
print("PERSISTENT URLs  (all categories combined)")
print(f"  Count          : {pers_total:,}")
print(f"  % of total     : {pers_pct:.2f}%")
print(f"  Active count   : {pers_active:,}")
print(f"  Activity %     : {pers_act_pct:.2f}%")
print()

# ─── Per-category table ───────────────────────────────────────────────────────

rows = []
for cat_name, _ in PERSISTENT_CATEGORIES:
    sub   = df[df[f"_pers_{cat_name}"]]
    cnt   = len(sub)
    act   = int(sub['is_active'].sum())
    rows.append({
        "category":     cat_name,
        "count":        cnt,
        "pct_of_total": round(cnt / total * 100, 3) if total else 0.0,
        "active":       act,
        "activity_pct": round(act / cnt * 100, 2) if cnt else 0.0,
    })

cat_df = pd.DataFrame(rows).sort_values("count", ascending=False)

print("─" * 65)
print("PER-CATEGORY BREAKDOWN")
print(cat_df.to_markdown(index=False))
print()

# ─── Overall summary ─────────────────────────────────────────────────────────

overall_active     = int(df['is_active'].sum())
overall_active_pct = overall_active / total * 100 if total else 0

print("=" * 65)
print("SUMMARY")
print(f"  Total URLs              : {total:,}")
print(f"  Overall active          : {overall_active:,}  ({overall_active_pct:.2f}%)")
print(f"  Shortening URLs         : {short_total:,}  ({short_pct:.2f}% of total,  activity {short_act_pct:.2f}%)")
print(f"  Persistent URLs         : {pers_total:,}  ({pers_pct:.2f}% of total,  activity {pers_act_pct:.2f}%)")


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  DOI URLS PER YEAR  — % of total URLs that year
# ═══════════════════════════════════════════════════════════════════════════════

# Deduplicate: one row per (year, url_id) to avoid double-counting a URL cited
# by multiple papers published in the same year.
year_url_dedup = year_url_df.drop_duplicates(subset=['year', 'url_id']).copy()
year_url_dedup['is_doi'] = year_url_dedup['url'].apply(is_doi)

year_stats = (
    year_url_dedup
    .groupby('year')
    .agg(
        total_urls = ('url_id', 'count'),
        doi_urls   = ('is_doi',  'sum'),
    )
    .reset_index()
    .assign(doi_pct=lambda x: (x['doi_urls'] / x['total_urls'] * 100).round(2))
    .sort_values('year')
)

print()
print("=" * 65)
print("DOI URLs PER YEAR  (% of total URLs cited that year)")
print(year_stats.to_markdown(index=False))
print()
