import asyncio
import playwright
import logging as log
from playwright.async_api import async_playwright, Playwright

async def run(playwright: Playwright):
    chromium = playwright.chromium
    browser = await chromium.launch()
    context = await browser.new_context(color_scheme="dark")
    page = await context.new_page()
    await page.goto("https://anshuman-8.vercel.app/")
    await page.screenshot(path="/home/anshuman/Anshu/Margati/PotentGPT/example.png")
    await browser.close()

async def login_google():
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        browser = await chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://accounts.google.com')
        await page.fill('input[type="email"]', 'anshuman.swain@margati.com')
        await page.click('div[id="identifierNext"]')
        await page.fill('input[type="password"]', 'your_password')
        await page.click('div[id="passwordNext"]')
        # Wait for the search results to load
        await browser.close()

async def perform_google_search(query):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Perform a Google search
        await page.goto('https://www.google.com')
        await page.type('textarea[name="q"]', query)
        await page.press('textarea[name="q"]', 'Enter')
        await page.wait_for_load_state('load')

        # Extract links from search results
        links = await page.query_selector_all('a')

        print(page.inner_text('body'))

        # write to file
        with open("./testings/links.txt", "w") as f:
            print([link.__getattribute__("href") for link in links])
            # for link in links:
            #     print(link)
            #     f.write(link + "\n")

        # search_results = [await link.get_attribute('href') for link in links]
        # print(search_results)

        # if search_results:
        #     top_result = search_results[0]
        #     await page.goto(top_result)
        #     await page.wait_for_load_state('load')

        #     # Extract content from the top website
        #     content = await page.inner_text('body')

        #     # Close the browser
        #     await context.close()

        #     return content

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(perform_google_search("Web development"))

