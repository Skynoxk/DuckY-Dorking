import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import (
    urlparse, parse_qs, parse_qsl, urljoin,
    urlencode, urlunparse
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

BASE_DDG = "https://html.duckduckgo.com/html/"

USER_AGENTS = [
    # A broader rotation to reduce repetition across runs
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]

DORKS = [
   "site:x.com CVE-2025"  # You can add more parameters here
]

# Engines to run; edit this list to enable/disable
DEFAULT_SEARCH_ENGINES = ["google", "bing", "brave", "duckduckgo"]


def random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def decode_duckduckgo_href(href: str) -> str | None:
    if not href:
        return None

    # Normalize scheme-relative or relative links
    if href.startswith("//"):
        href = "https:" + href
    elif href.startswith("/"):
        href = urljoin("https://duckduckgo.com", href)

    parsed = urlparse(href)

    # If it's a DuckDuckGo redirect (/l), extract and decode 'uddg' param
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l"):
        qs = parse_qs(parsed.query)
        target = qs.get("uddg", [None])[0]
        if target:
            # parse_qs already decodes the redirect's query parameter once.
            # Decoding again changes escaped delimiters inside the target URL.
            return target

    # Otherwise, if it's already a direct http(s) URL, return it
    if parsed.scheme in ("http", "https"):
        return href

    return None


def decode_google_href(href: str) -> str | None:
    if not href:
        return None
    if href.startswith("/url?"):
        qs = parse_qs(urlparse(href).query)
        target = qs.get("q", [None])[0]
        if target and target.startswith(("http://", "https://")):
            return target
    if href.startswith(("http://", "https://")):
        return href
    return None


def normalize_url(url: str) -> str:
    """
    Canonicalize URL for better de-duplication:
    - lowercase scheme/host
    - strip default ports
    - remove fragment
    - remove trailing slash on non-root paths
    - sort query parameters
    """
    p = urlparse(url)
    scheme = (p.scheme or "http").lower()
    host = (p.hostname or "").lower()

    # Handle default ports
    port = p.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    query = p.query
    if query:
        qsl = sorted(parse_qsl(query, keep_blank_values=True))
        query = urlencode(qsl, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))


def find_next_url_duckduckgo(soup: BeautifulSoup) -> str | None:
    # Try common "More Results/Next" selectors
    candidates = [
        "a.result--more__btn",
        "a.nav-link--next",
        "a.result__pagination__next",
        "a.result--more__btn.js-result-more",
    ]
    for sel in candidates:
        a = soup.select_one(sel)
        if a and a.get("href"):
            href = a["href"]
            if href.startswith("//"):
                return "https:" + href
            return urljoin(BASE_DDG, href)

    # Fallback: any anchor with text containing "Next"
    a = soup.find("a", string=re.compile(r"\bNext\b", re.I))
    if a and a.get("href"):
        href = a["href"]
        if href.startswith("//"):
            return "https:" + href
        return urljoin(BASE_DDG, href)

    return None


def iter_duckduckgo_results(query: str, max_pages: int = 5, pause: float = 1.0, session: requests.Session | None = None):
    s = session or requests.Session()

    next_url = f"{BASE_DDG}?{urlencode({'q': query})}"
    for _ in range(max_pages):
        r = s.get(next_url, timeout=30)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("a.result__a"):
            clean = decode_duckduckgo_href(a.get("href"))
            if clean:
                yield clean

        nxt = find_next_url_duckduckgo(soup)
        if not nxt:
            break

        next_url = nxt
        time.sleep(pause)


def iter_google_results(query: str, max_pages: int = 3, pause: float = 1.25, session: requests.Session | None = None):
    s = session or requests.Session()
    base = "https://www.google.com/search"
    for page in range(max_pages):
        params = {"q": query, "start": page * 10, "hl": "en"}
        r = s.get(base, params=params, timeout=30)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a"):
            clean = decode_google_href(a.get("href", ""))
            if clean:
                yield clean
        time.sleep(pause)


def iter_bing_results(query: str, max_pages: int = 3, pause: float = 1.0, session: requests.Session | None = None):
    s = session or requests.Session()
    base = "https://www.bing.com/search"
    for page in range(max_pages):
        params = {"q": query, "first": page * 10 + 1}
        r = s.get(base, params=params, timeout=30)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("li.b_algo h2 a, h2 a.b_title"):
            href = a.get("href", "")
            if href.startswith(("http://", "https://")):
                yield href
        time.sleep(pause)


def iter_brave_results(query: str, max_pages: int = 3, pause: float = 1.0, session: requests.Session | None = None):
    s = session or requests.Session()
    base = "https://search.brave.com/search"
    for page in range(max_pages):
        params = {"q": query, "offset": page * 10}
        r = s.get(base, params=params, timeout=30)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result-header, a.card-title, a[href^='http']"):
            href = a.get("href", "")
            if href.startswith(("http://", "https://")):
                yield href
        time.sleep(pause)


ENGINE_ITERATORS = {
    "duckduckgo": iter_duckduckgo_results,
    "google": iter_google_results,
    "bing": iter_bing_results,
    "brave": iter_brave_results,
}


def run_engine_once(engine: str, dork: str, max_pages: int, page_pause: float) -> set[str]:
    iter_fn = ENGINE_ITERATORS[engine]
    with requests.Session() as s:
        s.headers.update({"User-Agent": random_user_agent()})
        found: set[str] = set()
        for url in iter_fn(dork, max_pages=max_pages, pause=page_pause, session=s):
            try:
                norm = normalize_url(url)
                found.add(norm)
            except Exception:
                # Skip any URL that fails to normalize
                continue
        return found


def run_multi(
    dorks: list[str],
    runs: int = 4,
    max_pages: int = 6,
    page_pause: float = 1.0,
    run_pause: float = 2.0,
    max_results_per_dork: int | None = None,
    search_engines: list[str] | None = None,
    max_workers: int = 4,
):
    """
    - runs: how many times to repeat the search per dork
    - max_pages: pages per run per engine
    - page_pause: delay between pages
    - run_pause: delay between runs for the same dork
    - max_results_per_dork: optional cap after combining all runs
    - search_engines: list of engines to use
    - max_workers: threads to use for concurrent engine fetching
    """
    engines = search_engines or DEFAULT_SEARCH_ENGINES
    for d in dorks:
        combined: set[str] = set()
        print(f"Results for: {d}")

        for i in range(1, runs + 1):
            print(f"  Run {i}/{runs}:")
            run_added = 0
            with ThreadPoolExecutor(max_workers=min(max_workers, len(engines))) as pool:
                futures = {pool.submit(run_engine_once, eng, d, max_pages, page_pause): eng for eng in engines}
                for fut in as_completed(futures):
                    eng = futures[fut]
                    batch = fut.result()
                    before = len(combined)
                    combined |= batch
                    added = len(combined) - before
                    run_added += added
                    print(f"    [{eng}] fetched {len(batch)} (new unique: {added}, total unique: {len(combined)})")

            if max_results_per_dork is not None and len(combined) >= max_results_per_dork:
                print("    Reached max_results_per_dork limit; stopping early.")
                break

            # Small randomized pause between runs to reduce being throttled
            time.sleep(run_pause + random.uniform(0, 1.0))

        # Print final unique list (optionally trimmed to max_results_per_dork)
        final_list = list(combined)
        if max_results_per_dork is not None:
            final_list = final_list[:max_results_per_dork]

        for url in final_list:
            print(url)

        print(f"Total unique for '{d}': {len(final_list)}")
        print("-" * 40)


if __name__ == "__main__":
    print("Default Parameter :", DORKS)
    options = input("Do you want to input the parameter or use default (Y/N) ? ")
    if options in ("Y", "y"):
        parameter = input("Please input the parameter : ")
        print(parameter)
        DORKS.append(parameter)
    # Tune these as needed
    run_multi(
        DORKS,
        runs=2,  # Repeat each query 2 times (you can modify)
        max_pages=4,  # Pages to fetch per run per engine
        page_pause=1.0,  # Delay between pages
        run_pause=2.0,  # Delay between runs for same query
        max_results_per_dork=None,  # Or set a cap like 200
        search_engines=DEFAULT_SEARCH_ENGINES,
        max_workers=4,  # Threads for engines
    )
