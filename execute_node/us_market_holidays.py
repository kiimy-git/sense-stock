from playwright.sync_api import sync_playwright
import json

def scrape_us_holiday_notice():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # 페이지 접속
        ## 현재 사이트 휴장일 지원하지 않음 --------------> 변경 필요
        page.goto("https://m.hanwhawm.com:9090/M/main/oversea/main/OS001_1p.cmd")

        # table#_TBL_M 크롤링
        rows = page.query_selector_all("#_TBL_M tbody tr")
        result = []

        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) == 2:
                date = cells[0].inner_text().strip()  # 예: 2025/01/01
                desc = cells[1].inner_text().strip()  # 예: (미국) New Years Day
                result.append({
                    "date": date.replace("/", "-"),  # 날짜 포맷 정규화: 2025-01-01
                    "event": desc
                })

        browser.close()
        return result

if __name__ == "__main__":
    holidays = scrape_us_holiday_notice()

    # JSON 문자열로 출력 (n8n의 ExecuteCommand 노드에서 stdout 파싱 가능)
    print(json.dumps(holidays, ensure_ascii=False, indent=2))

