# For DuckDuckGo
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin, unquote, urlparse, parse_qs
from .SkyEngine import SkyEngine

class SkyDuck(SkyEngine):
    name = 'DuckDuckGo'
    BASE_URL = 'https://html.duckduckgo.com/html/'

    def query_url(self, query, page = 1) -> str:
        return f"{self.BASE_URL}?{urlencode({'q': query})}"

    def parse_result(self, soup: BeautifulSoup) -> list[str]:
        links = []
        for lnk in soup.select('a.result__a'):
            href = lnk.get('href')
            url = self.decode(href)
            if url:
                links.append(url)
        return links
    
    def next_page(self, soup) -> str | None:
        candidates = [
            'a.result--more__btn',
            'a.nav-link--next',
            'a.result__pagination__next',
            'a.result--more__btn.js-result-more',
        ]
        for sel in candidates:
            lnk = soup.select(sel)
            if lnk and lnk.get['href']:
                href = lnk['href']
                if href.startswith('//'):
                    return 'https:' + href
                return urljoin(self.BASE_URL, href)
        return None

    def decode(self, href) -> str | None:
        if not href:
            return None
        
        if href.startswith('//'):
            href = 'https:' + href
        elif href.startswith('/'):
            href = urljoin('https://duckduckgo.com', href)
        
        parsed = urlparse(href)

        if parsed.netloc.endswith('duckduckgo.com') and parsed.path.startswith('/l'):
            qs = parse_qs(parsed.query)
            target = qs.get('uddg', [None])[0]
            if target:
                return unquote(target)
            
        if parsed.scheme in ('http', 'https'):
            return href
        
        return None