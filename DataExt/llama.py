import os, json, re, requests
from typing import List, Dict, Any
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"
NUM_CTX = 128000
TEMPERATURE = 0.4

KEYS = [
        "전시회 국문명","영문명(Full Name)","영문명(약자)",
        "개최 시작","개최 종료",
        "개최장소(국문)","개최장소(영어)","국가","도시",
        "첫 개최년도","개최 주기","공식 홈페이지",
        "주최기관","담당자","전화","이메일",
        "산업분야","전시품목","출처"
    ]

# 추출 전략
def ask_ollama(system_prompt: str, before_user_prompt: list, before_assis_prompt: list, user_prompt: str) -> Dict[str, Any]:
    payload = {
        "model": MODEL,
        "options": {"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": before_user_prompt[0]},
            {"role": "assistant", "content": before_assis_prompt[0]},
            {"role": "user", "content": before_user_prompt[1]},
            {"role": "assistant", "content": before_assis_prompt[1]},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "").strip()

    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            return obj
        return {}
    except Exception:
        return {}
    
# LLM Model
def extract_from_text(text: str, keys: List[str]) -> Dict[str, Any]:
    system_prompt = (
        "너는 전시회 정보 추출 도우미다. 사용자가 제공한 텍스트에서 지정된 키만 찾아 "
        "정확한 JSON으로만 출력해라. 다음 규칙을 반드시 지켜라.\n"
        "[핵심 원칙]\n"
        "1) 절대 환각/추측 금지: 텍스트에 없는 정보는 \"\"(빈 문자열)로 둔다.\n"
        "2) 가능한 한 “원문 스팬”을 보존해 추출하되, 지정된 언어 규칙에 한해서만 번역한다.\n"
        "3) 여러 후보가 있으면 우선순위 규칙으로 선택한다.\n"
        "4) 출력은 지정된 키만 포함한 유효한 JSON이어야 한다(추가/누락/주석 금지).\n"
        "[언어 규칙]\n"
        "  - 전시회 국문명: 한국어, 영문명(Full Name)/영문명(약자): 영어(약자 없으면 "").\n"
        "  - 개최장소(국문): 한국어, 개최장소(영어): 영어 (개최장소 (국문, 영어) 둘 중 하나만 있으면 정확히 번역해서 짝을 맞춰줘).\n"
        "  - 국가/도시: 영어 표기(예: United States, Las Vegas).\n"
        "  - 날짜 형식: YYYY-MM-DD. 단일 월/연도만 있으면 가능한 한 보수적으로 보정(없으면 \"\")."
        "  - 전화/이메일/담당자: 텍스트에 없으면 \"\". 유사어/광고/문의 안내 문구를 억지로 쓰지 말 것.\n"
        "[전시회 명칭 선택 규칙]\n"
        "  - 전시회 국문명에 년도가 있으면 같이 넣어줘."
        "[검증/정규화]\n"
        "  - 국가/도시는 영어 대문자 규칙(고유명사) 준수.\n"
        "  - 공식 홈페이지는 전시회 외부 공식 사이트(행사/주최 측 도메인)를 우선. 본문에 없으면 "" (출처 URL과 혼동 금지).\n"
        "[출력 형식]\n"
        "  - 지정된 키만 포함한 단일 JSON 객체.\n"
        "  - 키의 순서는 호출자가 제공한 목록 순서를 따른다.\n"
        "  - 작업 과정이나 설명은 출력하지 마라. JSON 외 어떤 텍스트도 금지.\n"
    )
    before_user_prompt = [(
        "[예시 1]\n"
        "[입력 발췌]\n"
        "2025 미국 라스베가스 폐기물 재활용 전시회 [WE]\nWaste Expo\nWE\n2025.05.06 - 2025.05.08\nshare\n...개요\n미국 폐기물 처리 산업과 재활용 시설 및 제품 전시회 \n\n전시 안내\n \n개최기간 | 2025.05.06 - 2025.05.08 \n---|--- \n개최국가 | 미국 \n개최장소 | Las Vegas Convention Center \n개최규모 | 1000000sqft (ft²) \n산업분야 | 물류&운송, 기계&장비, 환경&폐기물 \n전시품목 | 시설, 중장비, 운송, 처리 기술 및 시스템 \n\n주최자\n \n주최기관 | Informa Market \n---|--- \n담당자 | \n전화 | 212-520-2700 \n팩스 | \n이메일 | informamarkets@informa.com \n홈페이지 | [www.wasteexpo.com]\n"
    ), (
        "[예시 2]\n"
        "[입력 발췌]\n"
        "# 미국 폐기물 및 재활용 전시회 2026(Waste Expo 2026)...n2027년 05월 03일(월) - 06일(목)\nLas Vegas Convention Center (LVCC)\n박람회 모든 회차 보기\n[ 2027년592일 남음 미국 폐기물 및 재활용 전시회 202605월 03일 ~ 05월 06일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 ](https://myfair.co/exhibition/116504)[ 2025년종료됨 미국 폐기물 및 재활용 전시회 202505월 06일 ~ 05월 08일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 ](https://myfair.co/exhibition/107471)[ 2024년종료됨 미국 폐기물 및 재활용 전시회 2024 05월 07일 ~ 05월 09일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 ](https://myfair.co/exhibition/95526)[ 2023년종료됨 미국 폐기물 및 재활용 전시회 2023 05월 01일 ~ 05월 04일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 ](https://myfair.co/exhibition/92365)[ 2022년종료됨 미국 폐기물 및 재활용 전시회 2022 05월 09일 ~ 05월 12일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 ](https://myfair.co/exhibition/80988)[ 2021년종료됨 미국 폐기물 및 재활용 전시회 2021 06월 28일 ~ 06월 30일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 ](https://myfair.co/exhibition/68885)[ 2020년취소됨 미국 폐기물 및 재활용 전시회 2020 05월 04일 ~ 05월 07일 ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 뉴올리언스 ](https://myfair.co/exhibition/48420)\n구독하기\n공유하기\n![twitter-x](https://myfair.co/images/globals/icon/twitter-x.svg)\n인기 박람회 - 2024년 환경 기업이 가장 많이 선택한 박람회입니다.\n부스 마감 기한 - 2027년 1월 경 부스 마감이 예상됩니다.\n박람회 정보공동관 기획∙운영자주 묻는 질문\n## 기본 정보\n개최 일정 | 2027년 05월 03일(월) - 06일(목) | 개최 국가/도시 | ![USA](http://purecatamphetamine.github.io/country-flag-icons/3x2/US.svg)미국 라스베이거스 \n---|---|---|--- \n개최 장소 | Las Vegas Convention Center (LVCC) | 개최 시간 | 10:00 ~ 17:00 \n단, 마지막 날은 13:00까지 \n개최 주기 | 1회 / 2년 | 첫 개최년도 | 1968년 \n참가기업 수 | 600개사 | 참관객 수 | 14,500명 \n 추가 정보\n미국 폐기물 및 재활용 전시회(Waste Expo)는 미국에서 매년 개최되는 북미 최대의 폐기물 관리 및 재활용 산업 박람회로, 최신 폐기물 관리 기술, 재활용 솔루션, 지속 가능한 자원 관리 시스템 등을 선보이는 글로벌 행사입니다. 이 박람회는 폐기물 관리 업계의 제조업체, 기술 공급업체, 정책 결정자, 연구자들이 모여 최신 기술을 공유하고 협력 기회를 확대하는 중요한 자리입니다. <전시 참가 목적> (1) 북미 폐기물 관리 시장 진출 북미는 폐기물 관리 및 재활용 기술이 급성장하는 지역으로, Waste Expo는 글로벌 기업들이 북미 시장에 진출하거나 입지를 강화할 기회를 제공합니다. (2) 혁신적인 폐기물 관리 기술 홍보 참가 기업들은 스마트 폐기물 관리 시스템, 재활용 기술, 바이오가스 솔루션 등 최신 제품과 기술을 선보이며, 업계 리더와 바이어들의 주목을 받을 수 있습니다. (3) 글로벌 네트워킹 및 협력 강화 폐기물 관리 업체, 기술 공급업체, 정책 결정자들이 모여 협력 기회를 탐색하고 장기적인 파트너십을 구축할 수 있습니다. <전시 카테고리> Waste Expo는 폐기물 관리 및 자원 재활용 산업의 다양한 분야를 포괄하며, 주요 카테고리는 다음과 같습니다: 폐기물 수집 및 운송 기술, 스마트 폐기물 관리 솔루션, 재활용 기술 및 설비, 바이오가스 및 에너지 회수, 환경 친화적 폐기물 처리, 정책 및 교육 <전시 특징> (1) 북미 최대의 폐기물 관리 및 재활용 박람회 Waste Expo는 약 600개 이상의 글로벌 기업과 14,000명 이상의 업계 전문가 및 바이어가 참여하는 대규모 행사로, 최신 트렌드와 기술을 제공합니다. (2) 혁신적인 제품 및 기술 전시 참가 기업들은 폐기물 관리 및 재활용 산업의 최신 기술과 솔루션을 선보이며, 글로벌 시장에서 브랜드를 강화할 기회를 제공합니다. (3) 전문 컨퍼런스 및 세미나 지속 가능한 자원 관리, 스마트 폐기물 관리 솔루션, 재활용 기술의 발전 등을 주제로 한 전문 컨퍼런스와 세미나가 함께 진행됩니다. (4) 지속 가능성과 환경 강조 폐기물 관리 산업의 환경적 영향을 줄이고 지속 가능한 기술을 도입하기 위한 특별 세션과 전시가 마련됩니다. Waste Expo는 폐기물 관리 및 자원 재활용 산업의 중심에서 최신 기술과 혁신을 공유하며, 참가 기업들에게 글로벌 협력과 비즈니스 확장의 기회를 제공하는 중요한 행사입니다."
    )
    ]
    before_assis_prompt = [(
        json.dumps({
            "전시회 국문명": "2025 미국 라스베가스 폐기물 재활용 전시회",
            "영문명(Full Name)": "Waste Expo",
            "영문명(약자)": "WE",
            "개최 시작": "2025-05-06",
            "개최 종료": "2025-05-08",
            "개최장소(국문)": "라스베이거스 컨벤션 센터",
            "개최장소(영어)": "Las Vegas Convention Center",
            "국가": "United States",
            "도시": "Las Vegas",
            "첫 개최년도": "",
            "개최 주기": "Annual",
            "공식 홈페이지": "https://www.wasteexpo.com",
            "주최기관": "Informa Markets",
            "담당자": "",
            "전화": "212-520-2700",
            "이메일": "informamarkets@informa.com",
            "산업분야": "Logistics, Machinery, Environment & Waste",
            "전시품목": "Facilities, Heavy Equipment, Transport, Processing Tech & Systems",
            "출처": "https://example.com"
            }, ensure_ascii=False)), 
        (
        json.dumps({
            "전시회 국문명": "미국 폐기물 및 재활용 전시회 2026",
            "영문명(Full Name)": "Waste Expo 2026",
            "영문명(약자)": "",
            "개최 시작": "2027-05-03",
            "개최 종료": "2027-05-06",
            "개최장소(국문)": "라스베이거스 컨벤션 센터",
            "개최장소(영어)": "Las Vegas Convention Center (LVCC)",
            "국가": "United States",
            "도시": "Las Vegas",
            "첫 개최년도": "1968 년",
            "개최 주기": "1회 / 2년",
            "공식 홈페이지": "https://www.wasteexpo.com/en/home.html",
            "주최기관": "",
            "담당자": "",
            "전화": "",
            "이메일": "",
            "산업분야": "폐기물 수집 및 운송 기술, 스마트 폐기물 관리 솔루션, 재활용 기술 및 설비, 바이오가스 및 에너지 회수, 환경 친화적 폐기물 처리, 정책 및 교육",
            "전시품목": "",
            "출처": ""
        }, ensure_ascii=False)
            )
    ]
    user_prompt = (
        "[출력 규칙]\n"
        f" - 키 목록: {keys}\n"
        "  - 너는 전시회 정보 추출 도우미다. 사용자가 제공한 텍스트에서 지정된 키만 찾아 정확한 JSON으로만 출력해라.\n"
        "  - JSON 외 텍스트 출력 금지"
        f"텍스트 시작:\n{text}\n텍스트 끝."
    )

    obj = ask_ollama(system_prompt, before_user_prompt, before_assis_prompt, user_prompt)

    # 누락 키 보정 + 후처리
    for k in keys:
        v = obj.get(k, "")
        if isinstance(v, str):
            v = v.strip()
        else:
            v = str(v)
        obj[k] = v

    for k in ["개최 시작", "개최 종료", "첫 개최년도"]:
        if k in obj:
            obj[k] = normalize_date(obj[k])
    return obj

# 날짜 정규화
def normalize_date(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    # 2025.05.06 / 2025-05-06 / 2025/5/6 / 2025년 5월 6일
    m = re.search(r"(\d{4})[.\-/\s년](\d{1,2})[.\-/\s월](\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # 2025.05 / 2025-5
    m = re.search(r"(\d{4})[.\-/\s년](\d{1,2})", s)
    if m:
        y, mo = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-01"
    return s

def run_pipeline_markdown(raw: dict): 

    text = (raw.get("markdown") or "").strip()

    if not text:
        print("처리할 텍스트가 없습니다.")
        return

    # 전체 텍스트 한 번만 추출
    print(f"[INFO] {MODEL} model 처리")
    rec = extract_from_text(text, KEYS)

    result = {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "model": MODEL,
        "num_ctx": NUM_CTX,
        "keys": KEYS,
        "data": rec,
    }

    return result