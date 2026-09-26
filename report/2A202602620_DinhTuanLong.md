# Member Role Report — Day 10: Data Pipeline & Data Observability

> Thông tin cá nhân, nhóm BLS và phạm vi dữ liệu ban đầu đã được xác nhận. Chủ báo cáo tự đọc và đánh dấu cam kết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đinh Tuấn Long |
| MSSV | 2A202602620 |
| Khóa/Lớp | K4 / L3B |
| Tên nhóm | BLS |
| Vai trò chính | Ingestion, cleaning, data quality và freshness |
| Repository | https://github.com/foxxiee04/K4-L3B-DAY10-BLS-DataPipelineDataObservability |
| Ngày soạn báo cáo | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref response/snapshot và Settings | Danh sách PaperRecord, hai raw JSON | Đã triển khai; snapshot đã kiểm tra; chưa xác nhận gọi API thật |
| Cleaning | `src/ingestion/cleaning.py`: `build_clean_dataframe` | PaperRecord và run_date | Bảng sạch, age_days, text_for_embedding; CSV/JSON qua bước lưu | Đã triển khai và kiểm tra local |
| Data quality | `src/observability/quality.py`: `run_data_quality_checks` | Bảng dữ liệu sạch hoặc bị lỗi | Báo cáo GX và trạng thái tổng hợp | Đã chạy local, baseline đạt |
| Freshness | `src/observability/quality.py`: `build_freshness_report` | published và age_days | Số dòng stale, tỷ lệ stale, is_fresh | Đã chạy local, baseline đạt |

Phạm vi trên dựa vào quá trình thực hiện trong phiên làm việc và commit `b6f083d` (tác giả Git: brxcewxyne, nội dung: done cleaning and quality gate). Chủ báo cáo cần xác nhận liên hệ tài khoản trước khi nộp. Code được triển khai với hỗ trợ của AI; tôi cần tự kiểm tra và giải thích được logic trước khi ký cam kết.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Bàn giao schema và artifact | Thành viên phụ trách test set, baseline và corruption/repair | Giữ nguyên chữ ký hàm, cung cấp paper_id, text_for_embedding, age_days và báo cáo quality |
| Đối chiếu kết quả tích hợp | Pipeline chung | Đã đối chiếu artifact trong repo; không nhận phần triển khai test set, index, orchestration và corruption của thành viên khác |

## 3. Kết quả theo vai trò

| Nhiệm vụ | Artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa raw metadata | `data/raw/crossref_records.json` | 24 bài theo schema PaperRecord | Đọc JSON và đếm record |
| Làm sạch dữ liệu | `data/clean/papers_clean.csv`, `papers_clean.json` | 24 dòng, có nội dung embedding 5 phần | Lệnh cleaning local và artifact đã lưu |
| Kiểm tra chất lượng | `data/quality/baseline_quality_report.json` | quality_success=True | Kết quả terminal local và JSON |
| Kiểm tra freshness | `data/quality/baseline_freshness_report.json` | is_fresh=True | Kết quả terminal local và JSON |

Output tiêu biểu là baseline_quality_report.json: thể hiện riêng kết quả GX, freshness và trạng thái tổng hợp, giúp nhóm phân biệt lỗi cấu trúc/nội dung với dữ liệu quá cũ.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Đầu vào Crossref có cấu trúc lồng nhau, trường tùy chọn và abstract chứa thẻ JATS. Dữ liệu phải được chuẩn hóa trước khi embedding, đồng thời giữ raw để truy vết và phục hồi.

### Cách triển khai

Ingestion chuyển DOI, title, abstract, author, subject và ngày thành PaperRecord. Mặc định ưu tiên snapshot; khi refresh được bật thì gọi API với timeout và tối đa ba lần thử, sau đó fallback về snapshot nếu thất bại. Chỉ lưu response mới sau khi parse ra dữ liệu dùng được.

Cleaning chuẩn hóa khoảng trắng và danh sách; loại dòng thiếu ID, title, summary hoặc ngày xuất bản hợp lệ. Khi trùng paper_id, giữ bản updated mới nhất. Ngày không timezone được xử lý theo UTC. age_days được tính theo ngày chạy, không sửa ngày xuất bản để tạo kết quả freshness đẹp hơn. text_for_embedding gồm Title, Authors, Published, Categories và Summary.

Quality dùng GX 1.x với ephemeral context và pandas batch. Các điều kiện gồm đủ số dòng theo max_results, paper_id duy nhất/không rỗng, các trường bắt buộc không null, title tối thiểu 8 ký tự và summary tối thiểu 50 ký tự. Hai ngưỡng độ dài là lựa chọn triển khai của nhóm. Freshness dùng ngưỡng 180 ngày; chỉ khi tỷ lệ stale lớn hơn 25% mới vi phạm SLA. Dữ liệu rỗng hoặc ngày/tuổi không hợp lệ không được coi là fresh.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref message.items; PaperRecord; DataFrame; Settings; run_date |
| Output | Raw records, DataFrame có metadata và helper columns, quality/freshness JSON |
| Module phụ thuộc | `core/config.py`, `core/utils.py`, pandas, requests, Great Expectations |
| Module sử dụng output | Test set, vector index, baseline pipeline, corruption và repair pipeline |
| Điều kiện lỗi cần xử lý | API timeout/429/5xx, snapshot lỗi, thiếu DOI/title, ngày sai, duplicate, summary rỗng, dữ liệu stale |

### Cách xác minh

Lệnh đã chạy trong CMD với môi trường Python 3.12.10:

```cmd
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; from observability.quality import run_data_quality_checks; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); r=run_data_quality_checks(df,s,'baseline'); print('Quality:',r['quality_success']); print('Freshness:',r['freshness']['is_fresh']); print('Overall:',r['success'])"
```

- Kết quả mong đợi: dữ liệu sạch đạt quality và freshness.
- Kết quả thực tế đã cung cấp từ terminal: Quality=True, Freshness=True, Overall=True.
- Artifact: `data/quality/baseline_quality_report.json`, `baseline_freshness_report.json`.
- Giới hạn: lần review này chưa chạy lại hai pipeline end-to-end; runtime mà công cụ review truy cập vẫn lỗi đường dẫn Python. Các chỉ số tích hợp dưới đây được đọc và đối chiếu từ artifact của nhóm, không nhận là kết quả tự chạy lại.

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: bài lab cần tái lập cùng dữ liệu và vẫn chạy khi API không truy cập được.
- Phương án cân nhắc: luôn gọi API mới hoặc ưu tiên snapshot, chỉ refresh khi yêu cầu.
- Phương án chọn: ưu tiên snapshot, refresh có retry/fallback.
- Lý do: giảm phụ thuộc mạng, giữ corpus ổn định để baseline và repair có thể đối chiếu; đổi lại phải theo dõi tuổi dữ liệu thay vì giả định snapshot luôn mới.
- Bằng chứng: raw/clean đều có 24 record; artifact repaired hiện trùng hoàn toàn clean baseline. Kiểm tra cô lập ingestion đã thử lỗi kết nối giả lập và fallback; chưa kiểm chứng API thật trong phiên này.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng: virtual environment cũ trỏ tới Python 3.12 không còn tại đường dẫn cấu hình, xuất hiện lỗi `No Python at ...`.
- Bước tái hiện: gọi Python trong `.venv` cũ.
- Nguyên nhân: đường dẫn interpreter nền của môi trường ảo không hợp lệ; máy có nhiều Python nên Python hệ thống không đồng nghĩa Python trong venv.
- Cách xử lý: thiết lập lại môi trường dùng Python 3.12 và kích hoạt trong CMD.
- Xác minh: terminal của tôi hiển thị Python 3.12.10; dòng đầu `where python` là `.venv\Scripts\python.exe`; lệnh quality chạy thành công.
- Điều học được: kiểm tra phiên bản và đường dẫn thực thi trước khi quy lỗi cho code/thư viện.

Môi trường công cụ review vẫn không thấy interpreter đó. Vì vậy không sử dụng kiểm tra cú pháp thay cho bằng chứng end-to-end.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được parse thành raw records, cleaning tạo metadata chuẩn và text_for_embedding; MiniLM tạo vector để lưu vào ChromaDB.
2. Test set có câu hỏi, đáp án chuẩn và ground_truth_doc_ids. Hit rate kiểm tra tài liệu chuẩn có nằm trong danh sách truy hồi; Token F1 so sánh câu trả lời với đáp án.
3. Quality kiểm tra số dòng, dữ liệu bắt buộc, tính duy nhất và độ dài. Freshness kiểm tra tỷ lệ bài vượt ngưỡng tuổi. Dữ liệu đúng schema vẫn có thể quá cũ.
4. Dùng cùng test set giúp giữ nguyên bài toán đo; nếu đổi câu hỏi giữa các trạng thái thì không thể quy thay đổi metric cho corruption/repair.
5. Repair cần tái tạo từ raw tin cậy, qua quality/freshness, xây lại index và đánh giá lại. Bằng chứng là clean/repaired data, báo cáo quality và các metrics, không chỉ exit code.

## 8. Phân tích kết quả

Các số liệu dưới đây thuộc phiên bản trước đợt sửa tích hợp. Chưa có kết quả end-to-end mới; phải chạy lại hai pipeline trước khi kết luận cho phiên bản nộp cuối.

### Metrics chính

Các số dưới đây lấy từ `data/results/*_metrics.json`, đối chiếu với `*_answers.json` và `data/quality/*_quality_report.json`.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.0 | 0.8 | 1.0 | Mất 2/10 retrieval hits rồi phục hồi |
| mean_token_f1 | 1.0 | 0.9 | 1.0 | Giảm 0.1 rồi phục hồi |
| judge_accuracy | 1.0 | 0.9 | 1.0 | Chưa so sánh công bằng vì baseline dùng heuristic fallback |
| mean_judge_score | 5.0 | 4.7 | 5.0 | Cần thống nhất judge trước khi kết luận |
| Quality checks | True | False | True | GX phát hiện dữ liệu bị lỗi |
| Freshness status | True | False | True | Tỷ lệ stale vượt ngưỡng ở trạng thái lỗi |
| Số dòng | 24 | 21 | 24 | Drop 5, duplicate 2, repair về 24 |
| Stale rows | 1 | 6 | 1 | Corrupted stale ratio 6/21 ≈ 28.57% |

### Kết luận từ số liệu

1. Sáu thao tác corruption làm giảm số dòng, tạo duplicate/title ngắn/summary rỗng và tăng tỷ lệ stale → quality/freshness chuyển False → hit rate giảm từ 1.0 xuống 0.8, Token F1 từ 1.0 xuống 0.9.
2. Tái tạo dữ liệu từ raw → clean/repaired trùng nhau và quality/freshness trở lại True → hai metrics trên trở lại 1.0.

Việc mất tài liệu benchmark có bằng chứng rõ đối với retrieval: hai câu không tìm thấy ground-truth document trong kết quả. Tuy nhiên cả sáu lỗi được áp dụng chung nên chưa có thí nghiệm riêng để xếp hạng tác động từng lỗi. Cần chạy từng lỗi độc lập để kết luận lỗi nào ảnh hưởng mạnh nhất.

Kết quả cần thận trọng: baseline đạt tuyệt đối nhưng `qa.py` bổ sung tài liệu exact-title lookup trước khi trích đáp án từ metadata; đây chưa phải phép đo riêng chất lượng semantic retrieval hay LLM Agent. Cả 10 baseline answers dùng heuristic judge fallback, trong khi corrupted/repaired không có nhãn fallback này. Do đó các judge metrics chưa đủ để khẳng định chất lượng chấm LLM nhất quán.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Giữ raw và document ID ổn định giúp truy vết, deduplicate và repair đúng nguồn.
2. Một pipeline chạy không lỗi vẫn có thể dùng dữ liệu stale; cần kiểm tra chất lượng và freshness riêng.
3. Đánh giá cần cùng test set và cơ chế chấm; baseline tuyệt đối không tự chứng minh LLM trả lời tốt.

### Nếu có thêm thời gian

Thêm kiểm thử tự động cho tuổi 180/181 ngày và tỷ lệ stale đúng 25%/vượt 25%, dữ liệu rỗng, null và duplicate. Chạy lại ba trạng thái với cùng judge, ghi rõ provider/model hoặc fallback. Tách semantic retrieval khỏi exact lookup để đo được đóng góp của embedding. Kiểm tra lại loading index trên máy khác vì manifest hiện chứa đường dẫn tuyệt đối của máy thành viên.

### Cập nhật sau review tích hợp

Đã bổ sung QA dùng LLM khi provider không phải mock, bỏ exact-title injection khỏi benchmark, quy định judge tường minh và kiểm tra cùng cấu hình/test set giữa các pha. Loader dùng đường dẫn Chroma của workspace hiện tại; báo cáo pha 1 được đưa về module reporting. Đây là phần hỗ trợ tích hợp với AI sau phân công ban đầu. Chưa có kết quả end-to-end mới nên giữ nguyên số liệu lịch sử và nêu rõ giới hạn.

## 10. Cam kết của thành viên

Các mục dưới đây để chủ báo cáo tự xác nhận sau khi đọc và chỉnh bản nháp:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đinh Tuấn Long

**Ngày xác nhận:** 26/09
