import time 
from playwright.async_api import async_playwright

async def searchExtraction(web_link:str):
    """
    Scrape the url and return the document, it also ignores assets
    """
    with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)
        web_content = ""
        metadata = {"website": web_link['link'],"source": web_link['source'], "title": web_link['title']}
        url = web_link['link']
        print(f"Scraping {url}...")
        t_start = time.time()
        try:
            page = await browser.new_page()
            excluded_resource_types = ["stylesheet", "script", "image", "font", "media"]

            async def route_handler(route):
                resource_type = route.request.resource_type
                if resource_type in excluded_resource_types:
                    await route.abort()
                else:
                    await route.continue_()

            await page.route(
                "**/*",
                route_handler
            )
            await page.goto(url, timeout=10000)
            web_content = await page.content()
            t_end = time.time()
            print(f"Content scraped for {url} in {t_end - t_start} seconds")
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        finally:
            await page.close()
        print(page_content=web_content, metadata=metadata)
        return web_content
    

link = "https://www.google.com"
data = searchExtraction(link)
print(data)