import asyncio
from quiz_scraper import QuizScraper

URL = "https://tds-llm-analysis.s-anand.net/demo"

async def main():
    try:
        async with QuizScraper(headless=True) as s:
            res = await s.scrape_quiz(URL)
            print("SCRAPE RESULT:", res)
    except Exception as e:
        import traceback
        print("EXCEPTION:", type(e).__name__, repr(e))
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
