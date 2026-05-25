import asyncio
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
import json
from collections import defaultdict
import re
from datetime import datetime

weekday_kr = {
    'Monday': '월요일',
    'Tuesday': '화요일',
    'Wednesday': '수요일',
    'Thursday': '목요일',
    'Friday': '금요일',
    'Saturday': '토요일',
    'Sunday': '일요일',
}

def convert_to_korean_date(date_str):
    """
    'Monday, July 21, 2025' → '2025년 7월 21일 월요일'
    """
    dt = datetime.strptime(date_str, "%A, %B %d, %Y")
    weekday = weekday_kr[dt.strftime("%A")]
    return f"{dt.year}년 {dt.month}월 {dt.day}일 {weekday}"


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
        # 1. 'Today'라는 텍스트를 가진 button 요소를 찾을 때까지 대기
        await page.wait_for_selector("button:has-text('Today')", timeout=15000)
        
        # 2. 해당 버튼 클릭
        await page.click("button:has-text('Today')")
        # ✅ 'td.theDay'를 기다리는 부분에 try-except 적용
        try:
            await page.wait_for_selector("td.theDay", timeout=7000)
        except TimeoutError:
            # TimeoutError가 발생하면 이 블록이 실행
            await browser.close()
            return {} # 빈 딕셔너리를 반환하고 함수를 종료

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="earningsCalendarData")

    # 항목은 고정이니까 수동으로 기입
    headers = ["종목명", "주당순이익(EPS)", "주당순이익_예측", "매출(Revenue)", "매출_예측", "총 시가"]
    result_by_date = defaultdict(list)
    current_date = None

    for row in table.select("tbody tr"):
        
        # ✅ 날짜 추출은 <tr> 내부의 <td>를 확인해야 함
        td = row.find("td", class_="theDay")
        if td:
            raw_date = td.get_text(strip=True)
            current_date = convert_to_korean_date(raw_date)
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
