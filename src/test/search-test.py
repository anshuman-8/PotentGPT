from search import Search
import json
import asyncio

async def main():
    query = "Violin tutors"
    location = "Santa Clara, CA"

    client = Search(query=query, location=location, country_code="US", timeout=10)

    response_gmaps = await client.search_google_business()

    web_results = await client.search_web()

    response_yelp = await client.search_yelp()

    # print("Printing Google Maps results")
    # with open("src/log_data/google_maps.json", "w") as f:
    #     f.write(json.dumps(response_gmaps, indent=2))

    print("Printing Yelp results")
    with open("src/log_data/yelp.json", "w") as f:
        # f.write(str(response_yelp))
        f.write(json.dumps(response_yelp, indent=2))
    # for result in response_yelp:
    #     print(result["title"])

    print("Printing Web results")
    with open("src/log_data/web.json", "w") as f:
        # f.write(str(web_results))
        f.write(json.dumps(web_results, indent=2))
    # for result in web_results:
    #     print(result["title"])




if __name__ == "__main__":
    asyncio.run(main())