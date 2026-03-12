#!/usr/bin/env python3
"""
URL content-category backfill with ordered heuristics (URL-only, no crawling).

Categories (in order):
  1) PAPER
  2) DATASET          (strict: explicit dataset sources/cues)
  3) ARTIFACT         (replication packages / supplementary research bundles)
  4) SOFTWARE
  5) PROJECT
  6) DOCUMENTATION

Modes:
  --url "<URL>"        Debug: run all steps for one URL and print per-step decisions
  --step {1..6}        Run only one step on all unclassified URLs
  --all                Run all steps on all unclassified URLs (default)

Env:
  DRY_RUN=1 (optional) — print what would be updated without writing to DB
"""

from __future__ import annotations

import os
import re
import sys
import argparse
from typing import Optional, Sequence, Tuple, Dict, List
from urllib.parse import urlparse, parse_qs, unquote

import psycopg2
import psycopg2.extras

sys.path.append('../')
from globalFunctions import config


# -----------------------------
# Configuration
# -----------------------------
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"


# -----------------------------
# DOI detection/extraction
# -----------------------------
DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
DOI_HOSTS = {"doi.org", "dx.doi.org"}


# -----------------------------
# Helpers (normalization + parsing)
# -----------------------------
_TRAILING_PUNCT_RE = re.compile(r"[)\],.;]+$")
_ARXIV_BARE_RE = re.compile(r"^(abs|pdf)/(\d{4}\.\d{4,5})(v\d+)?/?$", re.IGNORECASE)


def norm_host(host: str) -> str:
    return (host or "").lower().strip().rstrip(".")


def strip_protocol(url: str) -> str:
    u = (url or "").strip()
    u = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", u)
    return u.lstrip("/")


def normalize_url(url: str) -> str:
    s = (url or "").strip()
    if not s:
        return s

    s = _TRAILING_PUNCT_RE.sub("", s)

    try:
        s = unquote(s)
    except Exception:
        pass

    bare = strip_protocol(s)
    m = _ARXIV_BARE_RE.match(bare)
    if m:
        prefix = m.group(1).lower()
        arxiv_id = m.group(2)
        version = m.group(3) or ""
        return f"https://arxiv.org/{prefix}/{arxiv_id}{version}"

    return s


def get_host_path_query(url: str) -> Tuple[str, str, str]:
    raw = normalize_url(url)
    raw = (raw or "").strip()
    if not raw:
        return "", "", ""

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "http://" + raw

    try:
        p = urlparse(raw)
        return norm_host(p.netloc), (p.path or ""), (p.query or "")
    except ValueError:
        safe = raw.replace("[", "").replace("]", "")
        try:
            p = urlparse(safe)
            return norm_host(p.netloc), (p.path or ""), (p.query or "")
        except Exception:
            return "", "", ""


def url_tokens(url: str) -> List[str]:
    u = normalize_url(url)
    host, path, query = get_host_path_query(u)
    full = f"{host}{path}"
    if query:
        full += "?" + query
    full = full.lower()
    parts = re.split(r"[\/\?\&\=\#\:\.\-\_\+\s]+", full)
    return [p for p in parts if p]


def endswith_any(s: str, exts: Sequence[str]) -> bool:
    sl = (s or "").lower()
    return any(sl.endswith(ext) for ext in exts)


def startswith_any_schemeless(url: str, prefixes: Sequence[str]) -> bool:
    s = strip_protocol(normalize_url(url)).lower()
    if s.startswith("www."):
        s = s[4:]
    return any(s.startswith(p.lower()) for p in prefixes)


def extract_doi_from_url(url: str) -> Optional[str]:
    u = normalize_url(url)
    host, path, _ = get_host_path_query(u)

    if host in DOI_HOSTS:
        candidate = (path or "").strip("/").strip()
        if candidate:
            m = DOI_RE.search(candidate)
            if m:
                return m.group(1).lower()
            if candidate.lower().startswith("10."):
                return candidate.lower()

    m = DOI_RE.search(u)
    if m:
        return m.group(1).lower()
    return None


# -----------------------------
# Heuristic lists
# -----------------------------
# PAPER
PUBLISHER_HOSTS = {
    "dl.acm.org",
    "ieeexplore.ieee.org",
    "link.springer.com",
    "springer.com",
    "www.springer.com",
    "sciencedirect.com",
    "www.sciencedirect.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "www.tandfonline.com",
    "journals.sagepub.com",
    "academic.oup.com",
    "oup.com",
    "aclanthology.org",
    "drops.dagstuhl.de",
    "ceur-ws.org",
    "openreview.net",
}

PREPRINT_HOSTS = {
    "arxiv.org",
    "www.arxiv.org",
    "biorxiv.org",
    "www.biorxiv.org",
    "medrxiv.org",
    "www.medrxiv.org",
    "hal.science",
    "www.hal.science",
    "ssrn.com",
    "www.ssrn.com",
}

PAPER_PATH_SIGNATURES = (
    "/bitstream/",
    "/handle/",
    "/id/eprint/",
    "/eprint/",
    "/opus-",
    "/cgi/viewcontent.cgi",
)
URN_RESOLVER_HOSTS = {"nbn-resolving.org"}

PAPER_PDF_TOKENS = {
    "paper",
    "publication",
    "publications",
    "proceedings",
    "conference",
    "journal",
    "manuscript",
    "preprint",
    "accepted",
    "camera-ready",
    "cameraready",
    "final",
}
PAPER_PDF_ANTITOKENS = {
    "slides",
    "presentation",
    "tutorial",
    "manual",
    "documentation",
    "spec",
    "specification",
}

# DATASET (strict)
DATASET_PREFIXES_STRICT = [
    "kaggle.com/datasets/",
    "data.gov/",
    "catalog.data.gov/",
    "data.europa.eu/",
    "datadryad.org/",
    "openml.org/",
    "archive.ics.uci.edu/",
    "icpsr.umich.edu/",
    "huggingface.co/datasets/",
]

DATASET_FILE_EXTS = [
    ".csv", ".tsv", ".jsonl", ".parquet", ".h5", ".hdf5", ".arff", ".mat", ".npz", ".npy"
]

DATASET_TOKENS_STRICT = {
    "dataset",
    "datasets",
    "corpus",
    "benchmark",
    "benchmarks",
    "groundtruth",
    "ground-truth",
    "annotations",
    "annotated",
    "labels",
    "labelled",
}

DATASET_QUERY_KEYS = {"download", "files", "file", "filename"}

DATAVERSE_HOST_HINT = "dataverse."
DATAVERSE_PATH_HINT = "dataset.xhtml"

# Mixed artifact repositories
MIXED_ARTIFACT_HOSTS = {
    "zenodo.org", "www.zenodo.org",
    "figshare.com", "www.figshare.com",
    "osf.io", "www.osf.io",
}

ZENODO_RECORD_RE = re.compile(r"^/record/\d+/?", re.IGNORECASE)
FIGSHARE_DATASET_HINT = "/articles/dataset/"
OSF_DOWNLOAD_HINTS = ("/download", "/download/", "/files/", "/osfstorage/")

# ARTIFACT
ARTIFACT_TOKENS = {
    "artifact",
    "artifacts",
    "replication",
    "reproduction",
    "reproducibility",
    "supplementary",
    "supplement",
    "appendix",
    "materials",
    "package",
    "bundle",
    "dataset-and-code",
    "data-and-code",
    "code-and-data",
    "evaluation",
    "experiments",
    "results",
}

ARTIFACT_ARCHIVE_EXTS = [".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar"]

# SOFTWARE
SOFTWARE_HOSTS_EXACT = {"github.com", "gitlab.com", "bitbucket.org"}

SOFTWARE_VCS_HOSTS_EXACT = {
    "svn.apache.org",
    "git.apache.org",
    "hg.mozilla.org",
}
SOFTWARE_VCS_HOST_REGEXES = [
    re.compile(r"(^|\.)svn\.", re.IGNORECASE),
    re.compile(r"(^|\.)git\.", re.IGNORECASE),
    re.compile(r"(^|\.)hg\.", re.IGNORECASE),
]

SOFTWARE_PATH_CONTAINS = [
    (re.compile(r"(^|\.)sourceforge\.net$", re.IGNORECASE), "/projects/"),
    (re.compile(r"(^|\.)sourceforge\.net$", re.IGNORECASE), "/project/"),
]

PACKAGE_PREFIXES = [
    "pypi.org/project/",
    "cran.r-project.org/web/packages/",
    "www.npmjs.com/package/",
    "npmjs.com/package/",
    "rubygems.org/gems/",
    "packagist.org/packages/",
    "search.maven.org/artifact/",
    "repo.maven.apache.org/",
    "nuget.org/packages/",
    "ctan.org/pkg/",
]

HF_HOSTS = {"huggingface.co", "www.huggingface.co"}

ISSUE_TRACKER_TOKENS = {"jira", "bugzilla", "trac", "redmine", "youtrack"}

SOFTWARE_ARCHIVE_EXTS = [
    ".whl", ".jar", ".apk", ".exe", ".msi", ".dmg", ".deb", ".rpm",
    ".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar"
]
SOFTWARE_TOKENS = {"release", "releases", "source", "src", "code", "software", "repository", "repo", "commit", "tag"}

# PROJECT
PROJECT_TOKENS = {"project", "projects", "system", "systems", "platform", "framework", "initiative", "infrastructure", "tool", "tools"}
PROJECT_PATH_HINTS = ("/projects/", "/research/", "/systems/", "/tools/")
PROJECT_ANTITOKENS = {"docs", "documentation", "api", "manual", "guide", "tutorial", "reference"}

GOOGLE_SITES_HOSTS = {"sites.google.com"}
GOOGLE_SITES_PROJECT_HINTS = ("/view/", "/site/")

GITHUB_PAGES_SUFFIX = ".github.io"

NON_PROJECT_ROOT_HOSTS = {
    "google.com", "www.google.com",
    "bing.com", "www.bing.com",
    "yahoo.com", "www.yahoo.com",
    "youtube.com", "www.youtube.com",
    "facebook.com", "www.facebook.com",
    "twitter.com", "x.com", "www.x.com",
    "instagram.com", "www.instagram.com",
    "wikipedia.org", "en.wikipedia.org",
}

# DOCUMENTATION
DOC_HOSTS_EXACT = {"readthedocs.io", "developer.mozilla.org", "learn.microsoft.com"}
DOC_PATH_HINTS = (
    "/docs/",
    "/documentation/",
    "/manual/",
    "/guide/",
    "/tutorial/",
    "/howto/",
    "/how-to/",
    "/api/",
    "/reference/",
)
DOC_TOKENS = {"docs", "documentation", "manual", "guide", "tutorial", "howto", "api", "reference", "getting-started", "quickstart", "language"}
SLIDE_TOKENS = {"slides", "presentation", "ppt", "pptx", "talk", "lecture"}
SPEC_TOKENS = {"spec", "specification", "standard", "rfc", "w3c", "ietf"}


# -----------------------------
# DB I/O
# -----------------------------
def fetch_unclassified_urls(conn) -> List[Dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, url
            FROM urls
            WHERE content_category IS NULL
              AND url IS NOT NULL
              AND btrim(url) <> ''
            """
        )
        return list(cur.fetchall())


def update_categories(conn, updates: List[Tuple[int, str]]) -> None:
    if not updates:
        return
    if DRY_RUN:
        print(f"[DRY_RUN] Would update {len(updates)} rows")
        return
    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE urls SET content_category = %s WHERE id = %s AND content_category IS NULL",
            [(cat, uid) for (uid, cat) in updates],
        )


# -----------------------------
# Step implementations (single URL)
# Each returns (category or None, reason string)
# -----------------------------
def step1_paper(_: None, url: str) -> Tuple[Optional[str], str]:
    u = normalize_url(url)
    host, path, _ = get_host_path_query(u)
    path_l = (path or "").lower()
    toks = set(url_tokens(u))

    if host in PUBLISHER_HOSTS:
        return "PAPER", f"Publisher host match: {host}"
    if host in PREPRINT_HOSTS:
        return "PAPER", f"Preprint host match: {host}"

    if any(sig in path_l for sig in PAPER_PATH_SIGNATURES):
        return "PAPER", "Repository path signature match"
    if host in URN_RESOLVER_HOSTS and path_l.startswith("/urn:nbn:"):
        return "PAPER", "URN resolver match (urn:nbn:)"

    doi = extract_doi_from_url(u)
    if doi:
        if host not in MIXED_ARTIFACT_HOSTS:
            if not (toks & DATASET_TOKENS_STRICT) and not (toks & {"software", "code", "release", "source"}):
                return "PAPER", f"DOI detected (supporting): {doi}"

    is_pdf = endswith_any(path_l, [".pdf"]) or endswith_any(u.lower(), [".pdf"])
    if is_pdf:
        if toks & PAPER_PDF_ANTITOKENS:
            return None, "PDF but anti-paper tokens present (slides/manual/spec/etc)"
        if toks & PAPER_PDF_TOKENS:
            return "PAPER", "PDF + paper-context tokens match"
        if any(seg in path_l for seg in ("/papers/", "/publications/", "/pubs/", "/proceedings/", "/article/")):
            return "PAPER", "PDF + publication path segment match"

    return None, "No paper match"


def step2_dataset(_: None, url: str) -> Tuple[Optional[str], str]:
    """
    Strict datasets: only explicit dataset sources or strong dataset-only signatures.
    """
    u = normalize_url(url)
    host, path, query = get_host_path_query(u)
    path_l = (path or "").lower()
    toks = set(url_tokens(u))
    qs = parse_qs(query or "")
    qs_keys = {k.lower() for k in qs.keys()}

    if startswith_any_schemeless(u, DATASET_PREFIXES_STRICT):
        return "DATASET", "Matched strict dataset prefix"

    if DATAVERSE_HOST_HINT in host and DATAVERSE_PATH_HINT in path_l:
        return "DATASET", "Dataverse dataset.xhtml signature"

    if host.endswith("figshare.com") and FIGSHARE_DATASET_HINT in path_l:
        return "DATASET", "Figshare /articles/dataset/ signature"

    if host in MIXED_ARTIFACT_HOSTS:
        if host.endswith("zenodo.org") and ZENODO_RECORD_RE.match(path_l):
            has_dataset_tokens = bool(toks & DATASET_TOKENS_STRICT)
            has_downloadish = bool(qs_keys & DATASET_QUERY_KEYS) or any(t in toks for t in ("files", "download", "file", "filename"))
            has_dataset_ext = endswith_any(path_l, DATASET_FILE_EXTS) or any(
                any(v.lower().endswith(ext) for v in vals)
                for ext in DATASET_FILE_EXTS
                for vals in qs.values()
            )
            if has_dataset_tokens and (has_downloadish or has_dataset_ext):
                return "DATASET", "Zenodo record + dataset tokens + download/file signal"
            return None, "Zenodo record not strictly dataset"

        if host.endswith("osf.io"):
            has_downloadish = any(h in path_l for h in OSF_DOWNLOAD_HINTS) or ("osfstorage" in toks) or bool(qs_keys & DATASET_QUERY_KEYS)
            if has_downloadish and (toks & DATASET_TOKENS_STRICT):
                return "DATASET", "OSF download/storage + dataset tokens"
            if has_downloadish and endswith_any(path_l, DATASET_FILE_EXTS):
                return "DATASET", "OSF download/storage + dataset file extension"
            return None, "OSF not strictly dataset"

        if (toks & DATASET_TOKENS_STRICT) and (endswith_any(path_l, DATASET_FILE_EXTS) or bool(qs_keys & DATASET_QUERY_KEYS)):
            return "DATASET", "Mixed host + dataset tokens + file/download cue"

        return None, "Mixed host not strictly dataset"

    if endswith_any(path_l, DATASET_FILE_EXTS) and (toks & DATASET_TOKENS_STRICT):
        return "DATASET", "Dataset file extension + dataset tokens"

    return None, "No dataset match"


def step3_artifact(_: None, url: str) -> Tuple[Optional[str], str]:
    """
    ARTIFACT: replication packages / supplementary bundles (often data+code mixed).
    """
    u = normalize_url(url)
    host, path, query = get_host_path_query(u)
    path_l = (path or "").lower()
    toks = set(url_tokens(u))
    qs = parse_qs(query or "")

    if toks & ARTIFACT_TOKENS:
        if toks & SOFTWARE_TOKENS and host in SOFTWARE_HOSTS_EXACT:
            return None, "Artifact tokens present but on code host with software tokens (let software step decide)"
        return "ARTIFACT", "Artifact/replication/supplementary tokens match"

    if host in MIXED_ARTIFACT_HOSTS:
        if host.endswith("zenodo.org") and ZENODO_RECORD_RE.match(path_l):
            if any(t in toks for t in ("files", "download", "record", "records")):
                if toks & {"software", "source", "release", "code"}:
                    return "ARTIFACT", "Zenodo record + software-ish tokens (bundle-like)"
                return "ARTIFACT", "Zenodo record (ambiguous research bundle)"
            if any(any(v.lower().endswith(ext) for v in vals) for ext in ARTIFACT_ARCHIVE_EXTS for vals in qs.values()):
                return "ARTIFACT", "Zenodo record with archive download in query"
            return None, "Zenodo record with no artifact cues"

        if host.endswith("osf.io"):
            if any(h in path_l for h in OSF_DOWNLOAD_HINTS) or ("osfstorage" in toks):
                if not (toks & DATASET_TOKENS_STRICT) and not endswith_any(path_l, DATASET_FILE_EXTS):
                    return "ARTIFACT", "OSF download/storage (ambiguous bundle)"
                return "ARTIFACT", "OSF download/storage (bundle-like)"
            return None, "OSF no artifact cues"

        if host.endswith("figshare.com"):
            if endswith_any(path_l, ARTIFACT_ARCHIVE_EXTS):
                return "ARTIFACT", "Figshare archive file"
            if any(t in toks for t in ("supplementary", "materials", "artifact", "replication")):
                return "ARTIFACT", "Figshare supplementary/materials tokens"
            return None, "Figshare no artifact cues"

    if endswith_any(path_l, ARTIFACT_ARCHIVE_EXTS) or endswith_any(u.lower(), ARTIFACT_ARCHIVE_EXTS):
        if toks & (ARTIFACT_TOKENS | {"replication", "artifact", "supplementary", "materials", "experiment", "experiments", "results"}):
            return "ARTIFACT", "Archive extension + artifact/research-bundle tokens"
        if any(re.fullmatch(r"icse\d{4}", t) for t in toks) or any(re.fullmatch(r"ase\d{4}", t) for t in toks) or any(re.fullmatch(r"fse\d{4}", t) for t in toks):
            return "ARTIFACT", "Conference-year token + archive (replication package-like)"
        if any(re.fullmatch(r"\d{4}", t) for t in toks) and any(t in toks for t in ("replication", "artifact", "package", "supplementary")):
            return "ARTIFACT", "Year token + artifact tokens + archive"
        return None, "Archive extension but no artifact context"

    return None, "No artifact match"


def step4_software(_: None, url: str) -> Tuple[Optional[str], str]:
    u = normalize_url(url)
    host, path, _ = get_host_path_query(u)
    path_l = (path or "").lower()
    toks = set(url_tokens(u))

    if host in SOFTWARE_HOSTS_EXACT:
        return "SOFTWARE", f"Host exact match: {host}"
    for host_rx, seg in SOFTWARE_PATH_CONTAINS:
        if host_rx.search(host) and seg in (path or ""):
            return "SOFTWARE", f"Sourceforge project path match: {seg}"

    if host in SOFTWARE_VCS_HOSTS_EXACT:
        return "SOFTWARE", f"VCS host match: {host}"
    if any(rx.search(host) for rx in SOFTWARE_VCS_HOST_REGEXES):
        return "SOFTWARE", f"VCS host regex match: {host}"
    if any(seg in path_l for seg in ("/repos/", "/repo/", "/scm/", "/git/", "/svn/")) and any(
        t in toks for t in ("repos", "repo", "scm", "git", "svn", "tags", "trunk", "branches")
    ):
        return "SOFTWARE", "VCS path signature match"

    if startswith_any_schemeless(u, PACKAGE_PREFIXES):
        return "SOFTWARE", "Package registry prefix match"

    if host in HF_HOSTS:
        if not path_l.startswith("/datasets/") and path_l.strip("/"):
            return "SOFTWARE", "Hugging Face model/repo page"

    if toks & ISSUE_TRACKER_TOKENS:
        return "SOFTWARE", "Issue-tracker token match"

    if endswith_any(path_l, SOFTWARE_ARCHIVE_EXTS) or endswith_any(u.lower(), SOFTWARE_ARCHIVE_EXTS):
        if toks & SOFTWARE_TOKENS:
            return "SOFTWARE", "Archive/installer extension + software tokens"
        return None, "Archive extension but no software tokens (ambiguous)"

    return None, "No software match"


def step5_project(_: None, url: str) -> Tuple[Optional[str], str]:
    u = normalize_url(url)
    host, path, _ = get_host_path_query(u)
    path_l = (path or "").lower()
    toks = set(url_tokens(u))

    if toks & PROJECT_ANTITOKENS:
        return None, "Project skipped due to documentation tokens"

    if host and (path_l == "" or path_l == "/"):
        if host in NON_PROJECT_ROOT_HOSTS:
            return None, "Root path but known non-project portal host"
        if toks & DOC_TOKENS:
            return None, "Root path but documentation tokens present"
        return "PROJECT", "Root/empty path landing page"

    if host in GOOGLE_SITES_HOSTS and any(path_l.startswith(h) for h in GOOGLE_SITES_PROJECT_HINTS):
        return "PROJECT", "Google Sites /view|/site project page"

    if host.endswith(GITHUB_PAGES_SUFFIX):
        if any(h in path_l for h in ("/docs/", "/documentation/")) or (toks & DOC_TOKENS):
            return None, "GitHub Pages looks like docs (let documentation step decide)"
        return "PROJECT", "GitHub Pages site (project landing)"

    if toks & PROJECT_TOKENS:
        return "PROJECT", "Project/system keyword tokens match"

    if any(hint in path_l for hint in PROJECT_PATH_HINTS):
        if toks & {"project", "projects", "system", "systems", "tool", "tools", "framework", "platform"}:
            return "PROJECT", "Academic project path + project tokens"
        segs = [s for s in path_l.split("/") if s]
        if len(segs) <= 2:
            return "PROJECT", "Shallow research/systems/tools path (project-like)"

    segs = [s for s in path_l.split("/") if s]
    if host and len(segs) <= 1:
        if toks & {"about", "overview"}:
            return "PROJECT", "Landing/about/overview page (project-like)"

    return None, "No project match"


def step6_documentation(_: None, url: str) -> Tuple[Optional[str], str]:
    u = normalize_url(url)
    host, path, _ = get_host_path_query(u)
    path_l = (path or "").lower()
    toks = set(url_tokens(u))

    if host.endswith(GITHUB_PAGES_SUFFIX):
        if any(h in path_l for h in ("/docs/", "/documentation/")) or (toks & DOC_TOKENS):
            return "DOCUMENTATION", "GitHub Pages docs signals"

    if host.startswith("developer.") and (toks & DOC_TOKENS or any(h in path_l for h in DOC_PATH_HINTS)):
        return "DOCUMENTATION", "developer.* portal + docs signals"

    if host in DOC_HOSTS_EXACT:
        return "DOCUMENTATION", f"Documentation host match: {host}"
    if host.startswith("docs."):
        return "DOCUMENTATION", f"docs.* host match: {host}"

    if any(hint in path_l for hint in DOC_PATH_HINTS):
        return "DOCUMENTATION", "Documentation path hint match"

    if toks & DOC_TOKENS:
        return "DOCUMENTATION", "Documentation tokens match"

    if toks & SLIDE_TOKENS:
        return "DOCUMENTATION", "Slides/talk tokens match"

    if toks & SPEC_TOKENS:
        return "DOCUMENTATION", "Spec/standard tokens match"

    return None, "No documentation match"


STEP_FUNCS = {
    1: step1_paper,
    2: step2_dataset,
    3: step3_artifact,
    4: step4_software,
    5: step5_project,
    6: step6_documentation,
}


# -----------------------------
# Modes
# -----------------------------
def debug_url(url: str) -> None:
    print(f"Debug URL: {url}")
    for step in range(1, 7):
        cat, reason = STEP_FUNCS[step](None, url)
        print(f"Step {step}: cat={cat} | {reason}")
        if cat:
            print(f"-> FIRST MATCH: {cat} (pipeline stops here)")
            return
    print("-> No category assigned by steps 1..6 (content_category remains NULL)")


def run_single_step(conn, step: int) -> None:
    items = fetch_unclassified_urls(conn)
    print(f"Unclassified URLs: {len(items)}")
    fn = STEP_FUNCS[step]

    updates: List[Tuple[int, str]] = []
    for it in items:
        uid, url = it["id"], it["url"]
        cat, _ = fn(None, url)
        if cat:
            updates.append((uid, cat))

    print(f"Step {step} updates: {len(updates)}")
    update_categories(conn, updates)
    if not DRY_RUN:
        conn.commit()


def run_all_steps(conn) -> None:
    items = fetch_unclassified_urls(conn)
    print(f"Unclassified URLs: {len(items)}")

    for step in range(1, 7):
        fn = STEP_FUNCS[step]
        updates: List[Tuple[int, str]] = []
        remaining: List[Dict] = []

        for it in items:
            uid, url = it["id"], it["url"]
            cat, _ = fn(None, url)
            if cat:
                updates.append((uid, cat))
            else:
                remaining.append(it)

        print(f"Step {step} updates: {len(updates)} | remaining: {len(remaining)}")
        update_categories(conn, updates)
        if not DRY_RUN:
            conn.commit()
        items = remaining

    print(f"Remaining unclassified after Step 6: {len(items)}")
    if items:
        for it in items[:25]:
            print(f"  - ({it['id']}) {it['url']}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="URL content-category backfill (URL-only heuristics, no crawling)")
    p.add_argument("--url", type=str, help="Debug: run all steps on this single URL and print decisions")
    p.add_argument("--step", type=int, choices=range(1, 7), help="Run only this step (1..6) on all unclassified URLs")
    p.add_argument("--all", action="store_true", help="Run all steps on all unclassified URLs (default if no mode set)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    mode_debug = args.url is not None
    mode_single_step = args.step is not None
    mode_all = args.all or (not mode_debug and not mode_single_step)

    if mode_debug:
        debug_url(args.url)
        return

    db_params = config(filename='../database-setup/database.ini', section='postgresql')
    conn = psycopg2.connect(**db_params)
    conn.autocommit = False

    try:
        if mode_single_step:
            run_single_step(conn, args.step)
        if mode_all:
            run_all_steps(conn)
    finally:
        conn.close()

    if DRY_RUN:
        print("DRY_RUN=1 (no DB updates were written).")


if __name__ == "__main__":
    main()
