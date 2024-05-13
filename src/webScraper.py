import asyncio
import sys
import json
import time
import logging as log
from typing import Iterator, List, Tuple
from playwright.async_api import async_playwright
from langchain.docstore.document import Document
from src.utils import document2map
from src.config import Config
from src.model import Link
from src.data_preprocessing import preprocess_doc

LOG_FILES = False  # Logs the data (keep it False)

config = Config()


class AsyncChromiumLoader:
    def __init__(self, web_links: List[str]):
        self.web_links = web_links

    async def scrape_browser(self, web_links: List[Link]) -> List[Document]:
        """
        Scrape the urls by creating async tasks for each url
        """
        log.info(f"Starting scraping for {len(web_links)} sites...")
        results = []
        bt1 = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            bt2 = time.time()
            log.info(f"Browser launched in {(bt2-bt1):.3f} seconds")
            scraping_tasks = [
                self.scrape_url(browser, web_link) for web_link in web_links
            ]
            results = await asyncio.gather(*scraping_tasks, return_exceptions=True)
            await browser.close()
            log.debug(f"Browser closed")
            size_in_bytes = sys.getsizeof(results)
            size_in_mb = size_in_bytes / (1024 * 1024)
            log.info(
                f"Scraping done for {len(web_links)} sites, Size : {size_in_mb:.3f} MB"
            )
        
        return results

    async def scrape_url(self, browser, web_link: Link) -> List[Document]:
        """
        Scrape the url and return the document, it also ignores assets
        """
        processed_web_content = ""
        dur = -1
        secondary_links = []
        url = web_link.link
        log.info(f"Scraping {url}...")
        t_start = time.time()
        error = None
        try:
            page = await browser.new_page()
            excluded_resource_types = ["stylesheet", "script", "image", "font", "media"]

            async def route_handler(route):
                resource_type = route.request.resource_type
                if resource_type in excluded_resource_types:
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", route_handler)
            await page.goto(
                url, timeout=config.get_web_scraping_timeout(), wait_until="load"
            )
            web_content = await page.content()
            t_end = time.time()

            size_in_bytes = sys.getsizeof(web_content)
            size_in_kb = size_in_bytes / 1024
            dur = t_end - t_start
            log.info(
                f"Content scraped for {url} in {(dur):.2f} seconds, Size : {size_in_kb:.3f} KB"
            )
            processed_web_content, _secondary_links = preprocess_doc(web_content, web_link)
            secondary_links = _secondary_links
            
        except Exception as e:
            log.error(f"Error scraping {url}: {e}")
            error = e
        finally:
            try:
                await page.close()
            except Exception as e:
                log.error(f"Error closing page: {e}")
        metadata = {
            **web_link.getDocumentMetadata(),
            "scraping_time": dur,
            "error": error,
            "secondary_links": secondary_links,
        }
        result_doc = Document(page_content=processed_web_content, metadata=metadata)
        return result_doc

    async def load_data(self) -> Tuple[List[Document], List[Link]]:
        """
        Load the data from the urls asynchronously
        """
        secondary_links = []
        data = await self.scrape_browser(self.web_links)
        for doc in data:
            if isinstance(doc, Document):
                secondary_links.extend(doc.metadata.get("secondary_links", []))
                doc.metadata["secondary_links"] = []
            else:
                data.remove(doc)
        return data, secondary_links


async def scrape_with_playwright(web_links: List[Link]) -> List[dict]:
    """
    Scrape the websites using playwright and chunk the text tokens
    """
    t_flag1 = time.time()
    loader = AsyncChromiumLoader(web_links)
    docs, _secondary_links = await loader.load_data()
    t_flag2 = time.time()

    # FIXME : few document are error objects, and not Document objects
    if LOG_FILES:
        with open("src/log_data/docs.json", "w") as f:
            json.dump(document2map(docs), f)

    log.info(f"AsyncChromium Web scrape time : { t_flag2 - t_flag1}")

    secondary_links = list(set(_secondary_links))

    return docs, secondary_links
