import asyncio
import logging as log
from typing import Iterator, List

from langchain.docstore.document import Document

class AsyncChromiumLoader():
    """Scrape HTML pages from URLs using a
    headless instance of the Chromium."""

    def __init__(self,urls: List[str],):
        self.urls = urls

        try:
            import playwright 
        except ImportError:
            raise ImportError(
                "playwright is required for AsyncChromiumLoader. "
                "Please install it with `pip install playwright`."
            )

    async def ascrape_playwright(self, url: str) -> str:
        """
        Asynchronously scrape the content of a given URL using Playwright's async API.
        """
        from playwright.async_api import async_playwright

        log.info("Starting scraping...")
        results = ""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url)
                results = await page.content()  
                log.info("Content scraped")
            except Exception as e:
                results = f"Error: {e}"
            await browser.close()
        return results

    def lazy_load(self) -> Iterator[Document]:
        """
        Lazily load text content from the provided URLs.
        """
        for url in self.urls:
            log.info(f"Scraping {url}...")
            html_content = asyncio.run(self.ascrape_playwright(url))
            metadata = {"source": url}
            yield Document(page_content=html_content, metadata=metadata)

    def load(self) -> List[Document]:
        """
        Load and return all Documents from the provided URLs.
        """
        return list(self.lazy_load())
