# DuckDuckGo Dork Scraper (HTML endpoint)

A lightweight Python script to enumerate search results from DuckDuckGo’s HTML endpoint using common “dorks.” It rotates User-Agents, paginates through results, decodes DuckDuckGo redirect links, normalizes URLs for de-duplication, and aggregates unique results across multiple runs.

## Features

- Query one or more dorks (search strings) against html.duckduckgo.com.
- Follows “Next/More results” pagination.
- Decodes DuckDuckGo redirect links (uddg) into clean target URLs.
- Canonical URL normalization (scheme/host lowercasing, default-port stripping, sorted query params, no fragments) for reliable de-duplication.
- Simple randomized User-Agent and configurable pauses to reduce throttling.
- Supports multiple repeated runs per dork and optional max cap on results.

## Requirements

- Python 3.10+ (for modern type hints used in the script)
- Packages:
  - requests
  - beautifulsoup4

Install dependencies:
```bash
pip install requests beautifulsoup4
```

## Usage

Run the script directly:
```bash
python path/to/your_script.py
```

- You’ll be prompted whether to add a custom parameter (search query) or use the default defined in `DORKS`.
- Edit the `DORKS` list at the top of the script to add more default queries.
- Tuning knobs are passed to `run_multi` near the bottom of the file.

Example configuration in the script’s `__main__` section:
```python
run_multi(
    DORKS,
    runs=1,                 # How many times to repeat each query
    max_pages=8,            # Pages per run
    page_pause=1.0,         # Delay between pages (seconds)
    run_pause=2.0,          # Delay between runs (seconds)
    max_results_per_dork=None  # Optional cap on total unique results
)
```

### Example output
```text
Default Parameter :  ['inurl:php?id=1 site:th']
Do you want to input the parameter or use default (Y/N) ? N
Results for: inurl:php?id=1 site:th
  Run 1/1: fetched 42 (new unique: 42, total unique: 42)
https://example.com/page?id=1
https://another.example.th/item.php?id=1
...
Total unique for 'inurl:php?id=1 site:th': 42
----------------------------------------
```

## How it works

- Results are pulled from `https://html.duckduckgo.com/html/`.
- Each result link is cleaned:
  - DuckDuckGo redirect links (`/l?uddg=...`) are decoded to their target via the `uddg` parameter.
  - Plain http/https links are kept as-is.
- URLs are normalized to avoid duplicates across runs (lowercased scheme/host, strip default ports, remove fragments, sorted query parameters, no trailing slash for non-root paths).
- Pagination follows “Next/More results” links on the HTML page.
- Results are aggregated across runs for each dork and printed.

## Programmatic use

You can also import and use the helpers in your own code:

```python
from your_script import run_multi, run_once_for_dork, iter_duckduckgo_results, normalize_url

# Stream results for a single query
for url in iter_duckduckgo_results("inurl:login.php site:example.com", max_pages=5, pause=1.0):
    print(url)

# Collect unique, normalized results in one run
unique = run_once_for_dork("inurl:index.php?id= site:th", max_pages=6, page_pause=1.0)
print(len(unique), "unique URLs")

# Run multiple queries with repeats and timing controls
run_multi(
    ["inurl:php?id=1 site:th", "site:example.com inurl:admin"],
    runs=2,
    max_pages=6,
    page_pause=1.0,
    run_pause=2.0,
    max_results_per_dork=200
)
```

## Tips and caveats

- Throttling: If you see fewer pages than expected, increase `page_pause`, reduce `runs`, or try again later.
- Network robustness: Consider adding simple retry/backoff if your environment is flaky.
- Proxies: You can set `session.proxies` if needed before calling `iter_duckduckgo_results`.

## Legal and ethical notice

Only use this tool for lawful purposes. Respect websites’ Terms of Service and robots.txt where applicable. You are responsible for how you use this code and the data it collects.
