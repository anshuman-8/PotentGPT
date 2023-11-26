import asyncio
import playwright
import logging as log
from typing import Iterator, List
from playwright.async_api import async_playwright
from langchain.docstore.document import Document


class AsyncChromiumLoader:
    def __init__(self, urls: List[str]):
        self.urls = urls

    async def scrape_browser(self, urls: List[str]) -> List[Document]:
        """
        Scrape the urls by creating async tasks for each url
        """
        log.info("Starting scraping...")
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            scraping_tasks = [self.scrape_url(browser, url) for url in urls]
            results = await asyncio.gather(*scraping_tasks)
            await browser.close()
            log.debug(f"Browser closed")
        return results

    async def scrape_url(self, browser, url:str) -> Document:
        """
        Scrape the url and return the document
        """
        web_content = ""
        metadata = {"source": url}
        log.info(f"Scraping {url}...")
        try:
            page = await browser.new_page()
            await page.goto(url)
            web_content = await page.content()
            log.info(f"Content scraped for {url}")
        except Exception as e:
            log.error(f"Error scraping {url}: {e}")
        result_doc = Document(page_content=web_content, metadata=metadata)
        return result_doc

    def load_data(self) -> List[Document]:
        """
        Load the data from the urls asynchronously
        """
        data = asyncio.run(self.scrape_browser(self.urls))
        return data
