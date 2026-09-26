# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đình Anh Đức |
| MSSV               | 2A202602856 |
| Khóa/Lớp         | K4 - L3B |
| Tên nhóm         | BLS |
| Vai trò chính    | Corruption, Repair & Pipeline Integration |
| Repository         | https://github.com/foxxiee04/K4-L3B-DAY10-BLS-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Synthetic Data Corruption Suite | `src/ingestion/corruption.py` - `corrupt_clean_dataframe()` | Cleaned DataFrame gồm 24 bài báo | Corrupted DataFrame và `data/results/corruption_log.json` | Hoàn thành |
| Corruption và Repair Pipeline | `src/pipelines/corruption_flow.py` - `run_corruption_flow_pipeline()`, `repair_from_raw_snapshot()` | Baseline artifacts, raw snapshot và evaluation test set | Corrupted/repaired datasets, Chroma indexes, quality reports và metrics | Hoàn thành |
| Báo cáo đối chiếu ba trạng thái | `src/observability/reporting.py` - `generate_corruption_report()` | Metrics và quality/freshness của ba trạng thái | `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai sáu loại lỗi dữ liệu | `src/ingestion/corruption.py` | Corrupted dataset có 21 rows và log đủ 6 corruption | `data/results/corruption_log.json` |
| Kiểm tra dữ liệu corrupted bằng GX và Freshness SLA | `run_data_quality_checks()` | Quality gate và freshness đều chuyển sang `False` | `data/quality/corrupted_quality_report.json`, `corrupted_freshness_report.json` |
| Xây dựng và đánh giá index corrupted | Collection `papers-corrupted` | Retrieval Hit Rate giảm từ `1.0` xuống `0.8`; Token F1 giảm từ `1.0` xuống `0.9` | `data/results/corrupted_metrics.json` |
| Phục hồi dữ liệu từ raw snapshot | `repair_from_raw_snapshot()` | Khôi phục 24 records sạch, 24 ID duy nhất | `papers_clean_repaired.json` và repaired quality report |
| Xây dựng và đánh giá index repaired | Collection `papers-repaired` | Retrieval Hit Rate và Token F1 phục hồi về `1.0` | `data/results/repaired_metrics.json` |
| Sinh báo cáo đối chiếu ba trạng thái | `generate_corruption_report()` | Bảng Baseline vs Corrupted vs Repaired cùng phân tích quality/freshness | `data/reports/corruption_report.md` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh: `data/reports/corruption_report.md`:

```text
Data corruption
→ Quality Gate và Freshness SLA phát hiện lỗi
→ Retrieval/answer metrics suy giảm
→ Repair từ raw snapshot
→ Quality và metrics phục hồi về baseline
```

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline RAG có thể vẫn tiếp tục trả lời khi dữ liệu trong vector index bị thiếu, trùng lặp, lỗi nội dung hoặc quá cũ. Đây là hiện tượng Silent Failure: hệ thống không crash nhưng chất lượng retrieval và câu trả lời giảm.

Phần việc của tôi phải giải quyết ba vấn đề:

1. Tạo một bộ corruption có thể tái hiện và có log chi tiết.
2. Đo tác động của dữ liệu lỗi lên quality, freshness và RAG metrics.
3. Phục hồi dữ liệu an toàn từ raw snapshot thay vì sửa trực tiếp dữ liệu đã hỏng.

### Cách triển khai

Hàm `corrupt_clean_dataframe()` nhận cleaned DataFrame và tạo deep copy để không thay đổi baseline. 6 corruption được áp dụng theo thứ tự:

1. **Drop latest records:** sắp xếp theo `published` và loại 20% bài báo mới nhất.
2. **Blank summary:** đặt summary của hai records thành chuỗi rỗng.
3. **Inject noise:** thêm chuỗi nhiễu có thể nhận biết vào summary của 2 records.
4. **Truncate title:** cắt hai title xuống tối đa 7 ký tự, thấp hơn ngưỡng quality là 8 ký tự.
5. **Stale date:** lùi ngày xuất bản của 6 records đi 365 ngày và cập nhật đồng thời `age_days`.
6. **Duplicate rows:** nhân đôi 2 records nhưng giữ nguyên `paper_id`.

Sau tất cả thay đổi, `text_for_embedding` được dựng lại. Điều này bảo đảm ChromaDB nhận nội dung đã bị corruption thay vì embedding lại nội dung sạch cũ.

Mỗi corruption ghi lại:

- Loại lỗi.
- Số record bị tác động.
- Danh sách `paper_id`.
- Tham số đã sử dụng.

Corruption pipeline sau đó:

1. Lưu corrupted CSV/JSON.
2. Chạy GX và freshness checks.
3. Tạo collection `papers-corrupted`.
4. Đánh giá bằng test set baseline.
5. Đọc lại `data/raw/crossref_records.json`.
6. Chạy lại cleaning để tạo repaired DataFrame.
7. Tạo collection `papers-repaired`.
8. Đánh giá lại bằng cùng test set.
9. Sinh báo cáo đối chiếu 3 trạng thái.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `papers_clean.json`, `crossref_records.json`, `test_set.json`, baseline metrics và baseline quality report |
| Output                         | Corrupted/repaired CSV, JSON, embedding manifests, Chroma collections, metrics, quality reports và comparison report |
| Module phụ thuộc             | `core.config`, `core.utils`, `ingestion.cleaning`, `observability.quality`, `retrieval.index`, `evaluation.metrics` |
| Module sử dụng output        | Corruption report, báo cáo nhóm |
| Điều kiện lỗi cần xử lý | Thiếu baseline artifact; DataFrame rỗng hoặc thiếu cột; ngày không parse được; raw snapshot không hợp lệ; repaired quality không pass |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Corrupted quality/freshness fail, corrupted metrics giảm; repaired quality/freshness pass và repaired metrics phục hồi.
- **Kết quả thực tế:** Corrupted Hit Rate đạt `0.8`, Token F1 đạt `0.9`; repaired Hit Rate và Token F1 cùng trở lại `1.0`.
- **Artifact/log:**
  - `data/results/corruption_log.json`
  - `data/results/corrupted_metrics.json`
  - `data/results/repaired_metrics.json`
  - `data/quality/corrupted_quality_report.json`
  - `data/quality/repaired_quality_report.json`
  - `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau khi phát hiện dữ liệu corrupted, cần lựa chọn cách phục hồi dữ liệu.
- **Các phương án đã cân nhắc:**
  1. Sửa ngược từng lỗi trực tiếp trên corrupted DataFrame.
  2. Khôi phục hoàn toàn bằng cách đọc lại raw snapshot và chạy lại cleaning.
- **Phương án đã chọn:** Dựng lại repaired dataset từ `data/raw/crossref_records.json`.
- **Lý do:** Sửa trực tiếp dữ liệu lỗi dễ bỏ sót corruption, phụ thuộc vào thứ tự các phép sửa và khó bảo đảm idempotent. Raw snapshot là nguồn lineage chưa bị biến đổi, nên chạy lại cleaning cho kết quả ổn định, dễ kiểm tra và không che giấu lỗi.
- **Bằng chứng quyết định phù hợp:** Repaired dataset có 24 records, 24 ID duy nhất, quality/freshness đều pass. `papers_clean_repaired.json` giống baseline clean JSON và `repaired_metrics.json` giống baseline metrics.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sau khi lùi trường `published`, freshness có thể vẫn không chuyển sang `False`.
- **Lệnh hoặc bước tái hiện:** Tạo corrupted DataFrame chỉ thay đổi `published`, sau đó chạy `run_data_quality_checks()` và kiểm tra freshness report.
- **Nguyên nhân gốc:** Freshness checker sử dụng trực tiếp trường `age_days`; nó không tính lại tuổi dữ liệu từ `published`. Nếu chỉ thay đổi ngày xuất bản mà không thay đổi `age_days`, hai trường trở nên không nhất quán.
- **Cách xử lý:** Khi thực hiện corruption `stale_date`, cập nhật đồng thời:
  - `published = published - 365 ngày`;
  - `age_days = age_days + 365`;
  - dựng lại `text_for_embedding`.
- **Cách xác minh sau khi sửa:** `corrupted_freshness_report.json` ghi nhận 6/21 stale rows, stale ratio `0.285714`, vượt ngưỡng `0.25`, vì vậy `is_fresh=False`.
- **Điều học được:** Khi corruption một trường dẫn xuất hoặc trường nguồn, phải duy trì tính nhất quán giữa các trường liên quan. Nếu không, observability có thể bỏ sót lỗi hoặc báo kết quả không phản ánh dữ liệu thực tế.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Dữ liệu được đọc từ Crossref API/local snapshot, parse thành các `PaperRecord`, sau đó được cleaning, khử trùng lặp, tính `age_days` và tạo `text_for_embedding`. MiniLM biến `text_for_embedding` thành vector và lưu các vector cùng metadata vào ChromaDB.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Với mỗi câu hỏi, hệ thống lấy top-k documents từ index. Retrieval được xem là hit nếu một ID chuẩn xuất hiện trong các document lấy về. Câu trả lời được so với ground truth bằng Token F1 và judge score.
3. Quality checks kiểm tra cấu trúc và tính hợp lệ của dữ liệu, ví dụ row count, uniqueness, null và độ dài văn bản. Freshness monitoring đo mức độ cũ của dữ liệu thông qua `age_days` và stale ratio. Một dataset có thể đúng schema nhưng vẫn quá cũ, vì vậy hai loại kiểm tra bổ sung cho nhau.
4. Baseline, corrupted và repaired phải dùng cùng test set để thay đổi metrics chỉ phản ánh thay đổi dữ liệu/index. Nếu sinh test set mới cho từng trạng thái, phép so sánh sẽ không còn công bằng.
5. Repair được xem là thành công khi repaired dataset trở lại 24 records sạch, quality/freshness đều pass và các RAG metrics phục hồi bằng hoặc gần baseline. Trong kết quả hiện tại, repaired dataset và repaired metrics phục hồi hoàn toàn về baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0 | 0.8 | 1.0 | Corruption làm mất retrieval hit ở 20% test cases; repair phục hồi hoàn toàn |
| `mean_token_f1` | 1.0 | 0.9 | 1.0 | Answer quality giảm ít hơn hit rate vì một số document liên quan vẫn có nội dung gần ground truth |
| `judge_accuracy` | 1.0 | 0.9 | 1.0 | Giảm ở trạng thái corrupted và phục hồi sau repair |
| `mean_judge_score` | 5.0 | 4.7 | 5.0 | Mức suy giảm nhỏ nhưng có thể đo được |
| Quality checks | Pass | Fail | Pass | Corrupted data vi phạm row count, uniqueness, title length và summary checks |
| Freshness status | Pass | Fail | Pass | Stale ratio tăng từ 4.17% lên 28.57%, sau repair trở lại 4.17% |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi].
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi].

Corruption nào ảnh hưởng rõ nhất và vì sao?

1. Drop records, blank summary, truncated title, duplicates và stale dates làm quality gate chuyển từ `True` sang `False`; stale ratio tăng từ `0.0417` lên `0.2857`; Retrieval Hit Rate giảm từ `1.0` xuống `0.8` và Mean Token F1 giảm từ `1.0` xuống `0.9`.
2. Repair bằng cách đọc lại raw snapshot và chạy lại cleaning làm quality/freshness trở lại `True`; 24 records sạch được khôi phục; Retrieval Hit Rate và Mean Token F1 cùng trở lại `1.0`.

Corruption ảnh hưởng rõ nhất là **drop latest records**. Năm document mới nhất bị xóa hoàn toàn khỏi corrupted index, trong đó có document được benchmark tham chiếu. Khi ground-truth document không còn trong index, retrieval không thể tạo hit cho câu hỏi tương ứng. Điều này giải thích trực tiếp mức giảm Hit Rate từ `1.0` xuống `0.8`.

Kết quả nào khác với kỳ vọng ban đầu?

Token F1 chỉ giảm `0.1` dù Retrieval Hit Rate giảm `0.2`. Giả thuyết: Khi document chuẩn bị xóa, semantic search vẫn tìm được document có nội dung gần tương tự, nên một phần câu trả lời vẫn trùng với ground truth.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw data phải được bảo toàn như một lineage anchor. Khi downstream data bị lỗi, tái tạo từ nguồn raw đáng tin cậy an toàn hơn sửa trực tiếp dữ liệu corrupted.
2. Data observability cần kết hợp nhiều tín hiệu. Schema và quality checks phát hiện duplicate, missing hoặc malformed data; freshness phát hiện dữ liệu hợp lệ về cấu trúc nhưng đã quá cũ.
3. RAG có thể tiếp tục hoạt động dù dữ liệu bị lỗi. Vì vậy chỉ kiểm tra chương trình có crash hay không là chưa đủ; cần benchmark cố định và theo dõi retrieval/answer metrics để phát hiện Silent Failure.

### Nếu có thêm thời gian

Tôi sẽ bổ sung một corruption ablation test suite. Pipeline sẽ chạy 6 thí nghiệm độc lập, mỗi thí nghiệm chỉ kích hoạt 1 corruption và sử dụng cùng test set. Báo cáo sẽ bổ sung bảng:

```text
Corruption type
→ số record bị tác động
→ expectation bị fail
→ thay đổi Hit Rate
→ thay đổi Token F1
```

Cải thiện này giúp xác định chính xác corruption nào ảnh hưởng mạnh nhất thay vì chỉ đo tác động tổng hợp. Đồng thời, tôi sẽ cố định cùng một judge mode cho baseline, corrupted và repaired để bảo đảm judge metrics có thể so sánh trực tiếp.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đình Anh Đức
**Ngày xác nhận:** 2026-09-26
