import asyncio
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
import json
from collections import defaultdict

# 별점만 추출하는 함수 (이전과 동일)
def extract_star_rating(td):
    '''
    중요도 ★만 추출(예: ★☆☆, ★★☆, ★★★)
    '''
    full = len(td.find_all("i", class_="grayFullBullishIcon"))
    stars = "★" * full + "☆" * (3 - full)
    return stars

async def scrape_and_parse_tab(page, tab_selector):
    """
    주어진 tab_selector를 클릭하고 해당 탭의 데이터를 파싱하여 반환하는 함수
    """
    # print(f"🔄 {tab_selector} 탭을 클릭하고 데이터를 스크래핑합니다...")
    await page.click(tab_selector)
    
    try:
        # 데이터 로딩을 위해 잠시 대기 (네트워크 상태에 따라 조절 가능)
        await page.wait_for_selector("td.theDay", timeout=10000)
    except TimeoutError:
        print(f"⚠️ {tab_selector} 탭에서 데이터를 찾을 수 없습니다.")
        return defaultdict(list)

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="economicCalendarData")

    if not table:
        return defaultdict(list)

    headers = ["시간", "중요성", "이벤트", "실제", "예측", "이전"]
    result_by_date = defaultdict(list)
    current_date = None

    for row in table.select("tbody tr"):
        if "js-event-item" not in row.get("class", []):
            td = row.find("td", class_="theDay")
            if td:
                current_date = td.get_text(strip=True)
            continue

        flag = row.select_one("span.ceFlags")
        if not flag or "United_States" not in flag.get("class", []):
            continue
        
        cols = row.select("td")

        event_time = cols[0].get_text(strip=True)

        # '오늘' 탭(#timeFrame_today)일 경우, 08:00를 초과하는 데이터는 무시하고 반복 중단
        if tab_selector == "#timeFrame_today":
            if event_time > "08:00":
                # print(f"✅ '오늘' 탭에서 08:00 이후 데이터({event_time})이므로 수집을 중단합니다.")
                break
        
        # '어제' 탭(#timeFrame_yesterday)일 경우, 08:00 이전 데이터는 건너뛰기 (중복 방지)
        if tab_selector == "#timeFrame_yesterday":
            if event_time <= "08:00":
                # 이 시간대 데이터는 이전 실행 시 '오늘' 탭에서 이미 수집했으므로 건너뜁니다.
                continue

        if len(cols) < len(headers):
            continue

        values = [col.get_text(strip=True) for col in cols][:-1]
        
        importance_td = cols[2]
        importance = extract_star_rating(importance_td)
        values[2] = importance

        record = dict(zip(headers, values))
        
        if current_date:
            result_by_date[current_date].append(record)
            
    return result_by_date

async def scrape_us_events_combined():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://kr.investing.com/economic-calendar/", wait_until="domcontentloaded")
        
        # '어제' 탭 데이터 스크래핑
        yesterday_events = await scrape_and_parse_tab(page, "#timeFrame_yesterday")
        
        # '오늘' 탭 데이터 스크래핑
        today_events = await scrape_and_parse_tab(page, "#timeFrame_today")

        await browser.close()

        # 두 딕셔너리 결과 병합
        merged_events = yesterday_events.copy()
        for date, events in today_events.items():
            merged_events[date].extend(events)

        return merged_events

# --- 실행 부분 ---
if __name__ == "__main__":
    # 한국 시간 2025년 9월 4일 오전에 실행했다고 가정
    events = asyncio.run(scrape_us_events_combined())
    # print("\n✅ '어제'와 '오늘' 탭에서 수집된 모든 미국 이벤트:")

    print(json.dumps(events, indent=2, ensure_ascii=False))

