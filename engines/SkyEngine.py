# Base form for class
class SkyEngine:
    name = 'Browser'

    def query_url(self, query: str, page: int = 1) ->str:
        raise NotImplementedError
    
    def parse_result(self, soup) -> list[str]:
        raise NotImplementedError
    
    def next_page(self, soup) -> str | None:
        raise NotImplementedError
    
    def decode(self, href: str) -> str | None:
        return href