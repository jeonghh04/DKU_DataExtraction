import asyncio
import gradio as gr
import pyperclip
from crawl4ai import AsyncWebCrawler
from crawl4ai.chunking_strategy import RegexChunking
from pydantic import BaseModel, Field
from llama import *
from data import * 

# 크롤링할 페이지 데이터 정의
class PageSummary(BaseModel):
    title: str = Field(..., description="페이지 제목.")
    summary: str = Field(..., description="자세한 페이지 요약.")
    brief_summary: str = Field(..., description="간단한 페이지 요약.")
    keywords: list = Field(..., description="페이지에 할당된 키워드.")

#--------------- GRU 화면 표시 ----------------#

async def crawl_and_summarize(url):
    if not url:
        return "URL이 제공되지 않았습니다. 클립보드에 URL이 복사되어 있는지 확인해주세요."
    
    # ---------- Crawl4AI ---------- #
    async with AsyncWebCrawler(verbose=True) as crawler:
        start_time = time.time()
        result = await crawler.arun(
            url=url,
            word_count_threshold=1,
            chunking_strategy=RegexChunking(),
            bypass_cache=True,
        )
        raw_md = getattr(result, "markdown", "") or ""
        text_base = normalize_text(raw_md)

        record = {
            "markdown":  text_base or "",
            }

        bytes_norm = len((text_base or "").encode("utf-8"))

        print(f"[INFO] 전체 문장 길이: {bytes_norm} bytes")

        #--------------- LLM model ----------------#
        if not record:
            print("[INFO] 처리할 텍스트가 없습니다.")
            return
        
        result = run_pipeline_markdown(record)

        total_time = time.time() - start_time
        print(f"[INFO] 전체 걸린 시간: {total_time:.2f} s")
        return result

async def summarize_url(url):
    if not url:
        return "URL이 제공되지 않았습니다. 클립보드에 URL이 복사되어 있는지 확인해주세요."
    
    result = await crawl_and_summarize(url)
    if isinstance(result, str):
        return result
    if result:
        rec_raw = result["data"]
        rec = canonicalize_record(rec_raw)
        table_md = to_markdown_table(rec)
        pretty = to_json(rec)
        saved_path = save_json(result, rec, url)

        output = (
            "### 추출 결과(표)\n"
            f"{table_md}\n\n"
            "### Raw JSON(정리 후)\n"
            f"{pretty}\n"
            f"<sub>모델: {result['model']} · 컨텍스트: {result['num_ctx']} · 추출시각(UTC): {result['extracted_at']}</sub>"
            f"**JSON 저장:** `{saved_path}`"
        )

        print("[INFO] 처리 완료")
        return output, rec
    else:
        return f"페이지를 크롤링하고 요약하는 데 실패했습니다. 오류: {result.error_message}"

def run_summarize_url():
    try:
        url = pyperclip.paste()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result, rec = loop.run_until_complete(summarize_url(url))
        return url, result, rec
    except Exception as e:
        return "", f"오류가 발생했습니다: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("# 데이터 추출 하기")
    gr.Markdown("1. 브라우저에서 데이터 추출할 페이지의 URL을 복사하세요.")
    gr.Markdown("2. 'URL 붙여넣고 데이터 추출하기' 버튼을 클릭하세요.")

    matcher = FuzzyExhibitionMatcher(
                threshold=0.78,    # 부분 일치 허용 폭을 넓히고 싶으면 낮추세요 (예: 0.75~0.8)
                weight_kr=0.6,     # 국문명 가중치
                weight_en=0.4      # 영문명 가중치
            )

    with gr.Tabs():

        # ---------------- Tab 1: URL 크롤링 후 데이터 추출 ---------------- #
        with gr.Tab("URL로 추출"):
            gr.Markdown("1. 브라우저에서 데이터 추출할 페이지의 URL을 복사하세요.")
            gr.Markdown("2. 'URL 붙여넣고 데이터 추출하기' 버튼을 클릭하세요.")
            
            url_display = gr.Textbox(label="처리된 URL", interactive=True)
            summarize_button = gr.Button("URL 붙여넣고 데이터 추출하기")
            output = gr.Markdown(label="요약 결과")

            rec = gr.State(value=None)

            summarize_button.click(
                fn=run_summarize_url,
                outputs=[url_display, output, rec]
            )

        # ---------------- Tab 2: Json 비교 ---------------- #
        with gr.Tab("Json 비교"):
            gr.Markdown("URL로 추출한 JSON과 업로드한 JSON 파일을 비교합니다.")
            
            uploaded_json = gr.File(label="비교할 JSON 파일", file_types=[".json"])
            compare_button = gr.Button("비교하기")
            compare_output_tb2 = gr.Markdown(label="비교 결과")

            compare_button.click(
                fn=compare_with_uploaded,
                inputs=[rec, uploaded_json],  # URL 추출 JSON과 업로드 JSON
                outputs=compare_output_tb2
            )
        
        # ---------------- Tab 3: 데이터 비교 ---------------- #
        with gr.Tab("데이터 비교"):
            gr.Markdown("업로드한 2개의 JSON 파일을 비교합니다.")
            
            uploaded1_json = gr.File(label="비교할 JSON 파일", file_types=[".json"])
            uploaded2_json = gr.File(label="비교할 JSON 파일", file_types=[".json"])
            compare_button = gr.Button("비교하기")
            compare_output_tb3 = gr.Markdown(label="비교 결과")

            compare_button.click(
                fn=compare_with_json,
                inputs=[uploaded1_json, uploaded2_json],  # URL 추출 JSON과 업로드 JSON
                outputs=compare_output_tb3
            )

        # ---------------- Tab 3: 데이터 비교 ---------------- #
        with gr.Tab("DB 비교"):
            gr.Markdown("DB에 있는 JSON 파일과 비교합니다.")
            
            db_json = gr.State(r"C:\Users\user\ICAN_test\DataExt\data.json")
            uploaded_json = gr.File(label="비교할 JSON 파일", file_types=[".json"])
            compare_button = gr.Button("비교하기")
            compare_output_tb4 = gr.Markdown(label="비교 결과")

            compare_button.click(
                fn=matcher.compare_files,
                inputs=[db_json, uploaded_json],  # URL 추출 JSON과 업로드 JSON
                outputs=compare_output_tb4,
            )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7865)