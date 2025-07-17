## 📊 Sense Stock Data Repository

이 저장소는 **Sense Stock** 프로젝트에서 수집 및 생성한 데이터를 저장하고 관리하는 공간입니다. 

프로젝트 목적은 미국 주식 관련 뉴스와 시장 흐름을 자동 분석하여 투자 인사이트를 제공하는 것입니다.

---

### 📁 폴더 구조

```
├── heatmap/
│   └── 2025-05/         # 2025년 5월 S&P500 히트맵 이미지
│
├── execute_node         # Extract Data, Python Code
│
├── holidays/            # 미국 공휴일 정보 저장, ex)2025.json
│
├── reports/
│   └── 2025-06/         # 사용자 질문에 따른 자동 뉴스 분석 리포트
```

---

### 📌 사용 목적

- **`heatmap/`**: [Finviz](https://finviz.com/map.ashx)에서 S&P 500 히트맵 이미지를 수집하여 저장. 시장 참여자의 관심 흐름을 시각적으로 추적.
- **`execute_node/`**: [Finviz](https://finviz.com/map.ashx) 및 [Investing.com](https://kr.investing.com/)에서 경제/실적/S&P500 Data 추출 Code(Playwright)
- **`holidays/`**: 미국 증시 공휴일 데이터를 저장하여 비거래일 예측 및 일정 기반 분석에 활용.
- **`reports/`**: 사용자의 질문에 기반한 GPT 자동화 분석 결과를 저장하는 리포트 공간.

---

### 🗓️ 업데이트 주기

| 폴더명     | 업데이트 주기  |
|------------|-----------------|
| heatmap    | 매일 자동 수집(공휴일, 일요일, 월요일 제외)  |
| holidays   | 연 1회 자동 갱신|
| reports    | 요청 시 생성    |

---

### 🧠 블로그

👉 [프로젝트 블로그](https://cord-ai.tistory.com/category/n8n%2C%20Automation%20Tool/n8n%20Project)

---

### 🔒 기타 참고사항

- 이 저장소는 데이터 백업 및 관리 목적으로 사용됩니다.
- 일부 데이터는 수동으로 보완될 수 있습니다.
- 리포트 폴더 내 결과물은 모두 사용자 질문 기반입니다.

---
