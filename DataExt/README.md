# DataExtracion-llm
전시회 웹사이트에서 정보를 크롤링하고, LLM을 통해 데이터를 정제·구조화하여 JSON 형식으로 저장하는 프로젝트

## ✨ Features
- URL 입력만으로 전시회 정보 자동 크롤링
- 흔한 오타/표기 차이 보정 및 기타 전처리
- LLM 기반 텍스트 정제 및 구조화
- JSON  파일로 내보내기
- 전시회 제목, 개최 정보, 주최기관 등 주요 키 필드 자동 추출

## 🛠 Tech Stack
- Python 3.10+
- [crawl4ai](https://github.com/...) (비동기 크롤러)
- Olama
- pyqt
- Gradio (간단한 UI, 선택사항)

## 📦 Installation
```bash
git clone https://github.com/jeonghh04/DKU_DataExtraction.git
cd DKU_DataExtraction/DataExt
pip install -r requirements.txt

## 🚀 Usage
```bash
python main.py
http://127.0.0.1:7865 접속

## 📂 Output
결과는 outputs/ 폴더에 JSON 형태로 저장
```bash
{
    "전시회 국문명": "미국 폐기물 및 재활용 전시회",
    "영문명(Full Name)": "Waste Expo",
    "영문명(약자)": "",
    "개최 시작": "2025-05-06",
    "개최 종료": "2025-05-08",
    "개최장소(국문)": "라스베이거스 컨벤션 센터",
    "개최장소(영어)": "Las Vegas Convention Center (LVCC)",
    "국가": "미국",
    "도시": "라스베이거스",
    "첫 개최년도": "1968",
    "개최 주기": "1회/1년",
    "공식 홈페이지": "https://www.wasteexpo.com/en/home.html",
    "주최기관": "Informa Market",
    "담당자": "",
    "전화": "212-520-2700",
    "이메일": "informamarkets@informa.com",
    "산업분야": "물류, 운송, 기계, 장비, 환경, 폐기물",
    "전시품목": "시설, 중장비, 운송, 처리 기술 및 시스템",
    "출처": "GEP"
}
