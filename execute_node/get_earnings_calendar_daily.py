import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
from collections import defaultdict
import re

def parse_company_and_ticker(text):
    """
    '회사명(티커)' 형태의 문자열에서 분리
    예: "EpicQuest Education International(EEIQ)" → ("EpicQuest Education International", "EEIQ")
    """
    match = re.match(r"(.+?)\s*\((.+?)\)", text)
    if match:
        company_name = match.group(1).strip()
        ticker = match.group(2).strip()
        return company_name, ticker
    return text.strip(), None

def clean_prediction_value(text):
    """
    '/  5.57M' → '5.57M'
    """
    return text.replace("/", "").strip()

async def scrape_us_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://investing.com/earnings-calendar/", wait_until="domcontentloaded")
        await page.wait_for_selector("#timeFrame_yesterday", timeout=5000)

        # 🔄 '어제' 버튼 클릭"
        await page.click("#timeFrame_yesterday")
        await page.wait_for_selector("td.theDay", timeout=7000)

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="earningsCalendarData")

    # 항목은 고정이니까 수동으로 기입
    headers = ["회사", "주당순이익(EPS)", "주당순이익_예측", "매출(Revenue)", "매출_예축", "총 시가"]
    result_by_date = defaultdict(list)
    current_date = None

    for row in table.select("tbody tr"):
        
        # ✅ 날짜 추출은 <tr> 내부의 <td>를 확인해야 함
        td = row.find("td", class_="theDay")
        if td:
            current_date = td.get_text(strip=True)
            continue
        
        # 이벤트 행: <td> 요소들만 있음. Class를 걸러낼 필요가없음

        # ✅ 미국만 필터링(실적 사이트에선 Naming이 다름, ceFlags)
        flag = row.select_one("span.ceFlags")
        if not flag or "USA" not in flag.get("class", []):
            continue
        
        cols = row.select("td")
        # 요소(국가, 시간, 알림) => X
        values = [col.get_text(strip=True) for col in cols][1:-2]

        # 회사, 티커
        company_raw = values[0]
        company_name, ticker = parse_company_and_ticker(company_raw)
        values[0] = company_name

        # / 공백 제거
        values[2] = clean_prediction_value(values[2])
        values[-2] = clean_prediction_value(values[-2])

        # 이벤트 row 처리
        record = dict(zip(headers, values))
        if ticker:
            record["티커"] = ticker
        else:
            record["티커"] = None
        
        if current_date:
            result_by_date[current_date].append(record)
    
    return result_by_date

# 테스트
if __name__ == "__main__":
    events = asyncio.run(scrape_us_events())
    # print(f"\n✅ 총 추출 이벤트 수: {len(events)}")
    # print(json.dumps(events, indent=2, ensure_ascii=False))\
    print(json.dumps(events, indent=2, ensure_ascii=False))
