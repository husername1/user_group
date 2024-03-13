import asyncio
import requests
import json

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def get_soup_from_url(url: str) -> BeautifulSoup:
    """
    Uses Playwright to fetch HTML document.
    :param url: URL to fetch
    :type url: str
    :return: Parsed HTML document
    :rtype BeautifulSoup
    """
    async with async_playwright() as p:
        browser_type = p.chromium
        browser = await browser_type.launch_persistent_context("persistent_context")    # Keeps browser data to allow for faster runs of multiple pages
        page = await browser.new_page()

        await page.goto(url)

        await page.wait_for_timeout(5000)   # Wait to allow JS to populate page

        page_content = await page.content()
        soup = BeautifulSoup(page_content, 'html.parser')

    return soup


def get_product_list(soup: BeautifulSoup) -> list[BeautifulSoup | None]:
    """
    Searches for products table and lists product elements from within
    :param soup: bs4 object containing full parsed page
    :type soup: BeautifulSoup
    :return: List of product elements, or list of None
    :rtype: list[BeautifulSoup | None]
    """
    products_element = soup.find("div", {"class": "grid__products"})
    if products_element:
        product_list = products_element.find_all("div", {"class": "grid-product"})
    else:
        product_list = []

    return product_list


def get_product_data(product_list: list[BeautifulSoup | None]) -> dict[str, float]:
    """
    Gets all product names and prices from list of product elements.
    :param product_list: List of product element bs4 objects
    :type product_list: list[BeautifulSoup | None]
    :return: Dictionary mapping descriptions to prices
    :rtype: dict[str, float]
    """
    product_data = {}
    for product in product_list:
        title = (product.find("a", {"class": "grid-product__title"})
                 .find("div").encode_contents().decode("utf-8"))    # Description is contained within child element

        price_string = (product.find("div", {"class": "grid-product__price-value"})
                        .encode_contents().decode("utf-8"))
        price_float = float(price_string[1:])   # £ sign is removed then parsed to float for future mathematical operations
        product_data[title] = price_float

    return product_data


def scrape_pomprint_page(url: str) -> dict[str, float]:
    """
    Container function for running through functions that parse the page.
    :param url: Link to page containing products
    :type url: str
    :return: Fully parsed dict of product data from the page.
    :rtype: dict[str, float]
    """
    soup = asyncio.run(get_soup_from_url(url))

    product_list = get_product_list(soup)

    product_data = get_product_data(product_list)

    return product_data


def generate_pomprint_urls() -> list[str]:
    """
    Gets the JSON used for generating the webapp and uses it to generate urls for each school's product page.+
    :return: List of urls for each school's product page.
    :rtype: list[str]
    """
    # URL found by using browser's network monitor dev tool to look at requests made when loading the page.
    data_js_url = "https://app.store.prositehosting.co.uk/data.js?ownerid=60810823&lang=en&token=11aa93419f9eeedcfc159ede498311c12a4ecec4&callback=window.ecwid_initial_data.data.doInit"
    data_file_js = requests.get(data_js_url)

    raw_js_text = data_file_js.text

    raw_json = raw_js_text[:-1][38:]    # JS file is just a function call wrapping JSON data. This removes the call, leaving the data.

    parsed_json = json.loads(raw_json)

    url_list = []

    for category in parsed_json["categories"]:
        category_list = [109697278, 109697256, 109633495]   # These are the IDs for pre-schools, primary schools, and academies (pomprint also sells uniforms for clubs and activities.)
        parent_category = category.get("parent", None)  # None type default handles the cases for the parents.

        # This information was found by loading the file in browser, then manually looking through it with a JSON beautifier.
        if parent_category in category_list:
            url_list.append(f'https://www.pomprintdesigns.co.uk/?store-page={category["autogeneratedSlug"]}-c{category["id"]}')

    return url_list


def scrape_all_pomprint():
    """
    Parent function that collates site level data, uses other functions to generate urls then fetch and parse those urls.
    """
    all_data = {}
    url_list = generate_pomprint_urls()

    print(url_list)

    for url in url_list:
        all_data[url] = scrape_pomprint_page(url)


    with open("scraped_data.json", mode="w+", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, sort_keys=True)    # Indent and sort_keys are just to make the output more human-readable but are not required.

def main():
    scrape_all_pomprint()


if __name__ == "__main__":
    main()
