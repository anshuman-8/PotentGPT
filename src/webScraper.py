import asyncio
import time
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

    async def scrape_url(self, browser, url: str) -> Document:
        """
        Scrape the url and return the document, it also ignores assets
        """
        web_content = ""
        metadata = {"source": url}
        log.info(f"Scraping {url}...")
        t_start = time.time()
        try:
            page = await browser.new_page()
            excluded_resource_types = ["stylesheet", "script", "image", "font"] 
            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in excluded_resource_types
                else route.continue_(),
            )
            await page.goto(url, timeout=8000)
            web_content = await page.content()
            t_end = time.time()
            log.info(f"Content scraped for {url} in {t_end - t_start} seconds")
        except Exception as e:
            log.error(f"Error scraping {url}: {e}")
        finally:
            await page.close()
        result_doc = Document(page_content=web_content, metadata=metadata)
        return result_doc

    def load_data(self) -> List[Document]:
        """
        Load the data from the urls asynchronously
        """
        data = asyncio.run(self.scrape_browser(self.urls))
        return data
