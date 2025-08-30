import requests
from bs4 import BeautifulSoup
import time, random
from engines.utils import normalize_url
from engines.SkyDuck import SkyDuck
        
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
]

def random_user_agent() -> str:
    return random.choice(USER_AGENTS)

def iterate(engine, query: str, max_pages: int=5, pause: float=0.5, session: requests.Session | None=None):
    s = session or requests.Session()
    next_url = engine.query_url(query)
    for _ in range(max_pages):
        result = s.get(next_url, timeout=(3,6))
        if result.status_code != 200:
            break
        soup = BeautifulSoup(result.text, 'html.parser')
        
        for url in engine.parse_result(soup):
            try:
                yield normalize_url(url)
            except Exception:
                continue

        next_url = engine.next_page(soup)
        if not next_url:
            break
        
        time.sleep(pause)

def run_once_for_dork(engine, dork: str, max_pages: int, page_pause: float) -> set[str]:
    with requests.Session() as s:
        s.headers.update({"User-Agent": random_user_agent()})
        found: set[str] = set()
        for url in iterate(engine, dork, max_pages=max_pages, pause=page_pause, session=s):
            found.add(url)
        return found

def run_multi(engine, dorks: list[str],
              runs: int = 4,
              max_pages: int = 6,
              page_pause: float = 1.0,
              run_pause: float = 2.0,
              max_results_per_dork: int | None = None):
    
    for d in dorks:
        combined: set[str] = set()
        print(f"Results for: {d}")

        for i in range(1, runs + 1):
            batch = run_once_for_dork(engine, d, max_pages=max_pages, page_pause=page_pause)
            before = len(combined)
            combined |= batch
            added = len(combined) - before
            print(f"  Run {i}/{runs}: fetched {len(batch)} (new unique: {added}, total unique: {len(combined)})")

            if max_results_per_dork is not None and len(combined) >= max_results_per_dork:
                break

            time.sleep(run_pause + random.uniform(0, 1.0))

        final_list = list(combined)
        if max_results_per_dork is not None:
            final_list = final_list[:max_results_per_dork]

        for url in final_list:
            print(url)

        print(f"Total unique for '{d}': {len(final_list)}")
        print('-' * 40)

if __name__ == "__main__":
    DORKS = ['inurl:php?id=1 site:com']
    
    print("Default Parameter :", DORKS)
    options = input("Do you want to input the parameter or use default (Y/N) ? ")
    if options in ('Y', 'y'):
        parameter = input("Please input the parameter : ")
        print(parameter)
        DORKS.append(parameter)
    
    engine = SkyDuck()
    
    run_multi(
        engine,
        DORKS,
        runs=2,
        max_pages=8,
        page_pause=1.0,
        run_pause=2.0,
        max_results_per_dork=None
    )