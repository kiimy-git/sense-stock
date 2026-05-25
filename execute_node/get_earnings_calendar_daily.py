import asyncio
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
import json
from collections import defaultdict
import re
from datetime import datetime

# 영문 요일 번역용 사전
weekday_kr = {
    'Monday': '월요일', 'Tuesday': '화요일', 'Wednesday': '수요일',
    'Thursday': '목요일', 'Friday': '금요일', 'Saturday': '토요일', 'Sunday': '일요일'
}

async def run_with_retry(max_retries=3):
    """
    메인 크롤링 함수를 호출하고, 실패 시 브라우저를 닫고 다시 시도하는 래퍼 함수
    """
    for attempt in range(max_retries):
        try:
            print(f"\n🚀 크롤링 시도 [{attempt + 1}/{max_retries}]...")
            result = await scrape_us_events()
            if result:
                print("✅ 성공적으로 데이터를 수집했습니다.")
                return result
            else:
                raise Exception("데이터를 찾지 못했습니다.")
        except Exception as e:
            print(f"⚠️ 시도 [{attempt + 1}] 실패: {e}")
            if attempt == max_retries - 1:
                print("❌ 최대 재시도 횟수 초과. 종료합니다.")
                return {}
            await asyncio.sleep(2) # 재시도 전 대기

def clean_and_convert_date(raw_text):
    """
    'Monday, May 25, 2026' 형태를 '2026년 5월 25일 월요일'로 정밀 변환
    """
    # 1. 텍스트 주변에 붙은 쓸데없는 공백이나 문자열 제거
    cleaned = raw_text.strip()
    
    # 2. 정규식으로 날짜 포맷팅 골격만 정확히 추출 (Monday, May 25, 2026 구조 추출)
    date_match = re.search(r"([A-Za-z]+,\s*[A-Za-z]+\s*\d+,\s*\d{4})", cleaned)
    if date_match:
        target_str = date_match.group(1).strip()
    else:
        # 정규식이 실패하더라도 요일 단어가 있다면 텍스트 그대로 사용 시도
        target_str = cleaned

    try:
        # 파이썬 datetime 객체로 파싱 후 한국어 포맷으로 리턴
        dt = datetime.strptime(target_str, "%A, %B %d, %Y")
        weekday_str = weekday_kr[dt.strftime("%A")]
        return f"{dt.year}년 {dt.month}월 {dt.day}일 {weekday_str}"
    except Exception:
        # 혹시 파싱 에러나면 디버깅을 위해 원본이라도 반환
        return target_str

async def scroll_until_done(page, pause_time=1500, max_scrolls=60, stable_threshold=4):
    """
    일주일치 전체 데이터를 다 불러올 때까지 스크롤 및 더보기 제어
    """
    prev_count = 0
    stable_rounds = 0
    show_more_selector = "button:has-text('Show More'), button:has-text('더 보기'), [class*='showMore'], [id*='showMore']"

    for i in range(max_scrolls):
        for _ in range(3):
            await page.mouse.wheel(0, 2500)
            await page.wait_for_timeout(200)
            
        await page.wait_for_timeout(pause_time)

        try:
            show_more_btn = page.locator(show_more_selector).first
            if await show_more_btn.is_visible() and await show_more_btn.is_enabled():
                # print("🔘 'Show More' (더 보기) 버튼 발견! 클릭합니다.")
                await show_more_btn.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        row_count = await page.evaluate("""
            () => document.querySelectorAll("tbody[class*='datatable-v2_body'] tr").length
        """)
        # print(f"🔄 스크롤 [{i+1}/{max_scrolls}] - 현재 로드된 테이블 행 개수: {row_count}")

        if row_count == prev_count:
            stable_rounds += 1
            if stable_rounds >= stable_threshold:
                # print("✅ 모든 주간 데이터 로드 완료.")
                break
        else:
            stable_rounds = 0

        prev_count = row_count


async def scrape_us_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # print("🌐 인베스팅닷컴 영문 실적 캘린더 접속 중...")
        await page.goto("https://www.investing.com/earnings-calendar/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # 'Today' 클릭 전 기존 Today 테이블 강제 청소 (레이스 컨디션 방지 트릭)
        today_selector = "button:has(span:text('Today')), button:has-text('Today')"
        await page.wait_for_selector(today_selector, timeout=15000)
        
        await page.evaluate("""
            () => {
                const tbody = document.querySelector("tbody[class*='datatable-v2_body']");
                if (tbody) tbody.innerHTML = ""; 
            }
        """)
        
        await page.click(today_selector)
        # print("✅ 'Today' 필터 클릭 완료. 주간 데이터 로딩을 대기합니다.")
        
        try:
            await page.wait_for_selector("tbody[class*='datatable-v2_body'] tr", timeout=15000)
            await page.wait_for_timeout(2500)
        except TimeoutError:
            # print("🚨 데이터를 로드하지 못했습니다.")
            await browser.close()
            return {}

        # print("⏳ 주간 실적 데이터 무한 스크롤 다운 시작...")
        await scroll_until_done(page, pause_time=1500)
        \
        rows = await page.eval_on_selector_all(
            "tbody[class*='datatable-v2_body'] tr",
            "elements => elements.map(el => el.outerHTML)"
        )

        html = await page.content()

        await browser.close()


    # ==============================================================
    # 💡 뼈대 분석 및 정밀 데이터 바인딩 엔진
    # ==============================================================
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.select_one("tbody[class*='datatable-v2_body']")

    if not tbody:
        # print("🚨 테이블 본문을 찾지 못했습니다.")
        return {}

    result_by_date = defaultdict(list)
    current_date = None
    
    result_by_date = defaultdict(list)
    current_date = "미분류 일정"

    for row_html in rows:
        soup_row = BeautifulSoup(row_html, "html.parser")
        row = soup_row.find("tr")
        
        # [구조 파악]: 날짜 행은 'datatable-v2_row__hkEus'만 있고, 데이터 행은 ILVMx 클래스가 포함됨
        row_classes = row.get("class", [])
        
        # 1. 날짜 행인지 판별
        # 힌트: 날짜가 들어있는 div는 text-primary 클래스를 가짐
        date_div = row.find("div", class_="text-primary")
        if date_div:
            raw_date = date_div.get_text(strip=True)
            current_date = clean_and_convert_date(raw_date)
            # print(f"📅 날짜 변경 감지: {current_date}")
            continue # 날짜 행은 데이터가 없으므로 건너뜀

        # 2. 데이터 행 처리
        if "dynamic-table-v2_row__ILVMx" in row_classes:
            # 미국 기업인지 확인
            if not row.find(attrs={"data-test": "flag-US"}):
                continue
                
            cells = row.find_all("td")
            if len(cells) < 7: continue
            
            try:
                ticker = cells[1].select_one("a").get_text(strip=True) if cells[1].select_one("a") else "-"
                company = cells[1].get_text(strip=True).replace(ticker, "").replace("(", "").replace(")", "").strip()

                eps          = cells[2].get_text(strip=True)  
                eps_pred     = cells[3].get_text(strip=True)  
                revenue      = cells[4].get_text(strip=True)  
                revenue_pred = cells[5].get_text(strip=True)  
                market_cap   = cells[6].get_text(strip=True)  

                eps = eps.replace("/", "").strip() if eps else "-"
                eps_pred = eps_pred.replace("/", "").strip() if eps_pred else "-"
                revenue = revenue.replace("/", "").strip() if revenue else "-"
                revenue_pred = revenue_pred.replace("/", "").strip() if revenue_pred else "-"

                record = {
                    "종목명": company,
                    "티커": ticker,
                    "주당순이익(EPS)": eps,
                    "주당순이익_예측": eps_pred,
                    "매출(Revenue)": revenue,
                    "매출_예측": revenue_pred,
                    "총 시가": market_cap
                }
                
                # 매핑 타겟팅 지정
                target_key = current_date if current_date else "미분류 일정"
                result_by_date[target_key].append(record)
                    
            except Exception as e:
                continue

    return result_by_date


if __name__ == "__main__":
    events = asyncio.run(run_with_retry())
    print("\n🎉 이번주 미국 기업 실적 데이터 수집 완료!")
    print(json.dumps(events, indent=2, ensure_ascii=False))

# if __name__ == "__main__":
#     # 1. 크롤링 및 파싱 실행
#     events = asyncio.run(scrape_us_events())
    
#     # 2. 콘솔창 수집 통계 요약 검증
#     print(f"\n🎉 수집 완료! 총 {len(events)}일의 데이터가 분리되었습니다.")
#     for date, items in events.items():
#         print(f" - {date}: {len(items)}개 기업 수집됨")

#     # 3. 💾 JSON 파일 최종 물리 저장 파트
#     output_filename = "us_earnings_today.json"
    
#     with open(output_filename, "w", encoding="utf-8") as f:
#         # indent=2를 주어 줄바꿈 구조로 예쁘게 정렬하고, 한글 깨짐 방지를 위해 ensure_ascii=False 설정
#         json.dump(events, f, indent=2, ensure_ascii=False)
        
#     print(f"\n💾 최종 파일이 성공적으로 저장되었습니다: ./{output_filename}")