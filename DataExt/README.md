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
