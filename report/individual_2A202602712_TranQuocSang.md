# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Trần Quốc Sáng |
| MSSV | 2A202602712 |
| Khóa/lớp | K4-L3B |
| Tên nhóm | BLS |
| Repository | https://github.com/foxxiee04/K4-L3B-DAY10-BLS-DataPipelineDataObservability |
| Vai trò | Tích hợp baseline pipeline và tạo phase1_report |
| Ngày báo cáo | 26/09/2026 |

## 2. Phần việc tôi phụ trách

Tôi phụ trách ghép các bước đã được xây dựng ở những module khác thành luồng baseline chạy từ một lệnh. Phần tôi tập trung là `src/pipelines/phase1.py`: lấy dữ liệu nguồn, gọi bước làm sạch, lưu dữ liệu sạch, chạy kiểm tra chất lượng và freshness, tạo ChromaDB index, chuẩn bị bộ câu hỏi đánh giá, tính metrics rồi xuất báo cáo pha 1. Điểm bắt đầu của luồng là `script/run_phase1.py`.

Đầu vào của phần việc này là cấu hình trong `core/config.py`, dữ liệu Crossref hoặc snapshot raw, cùng các hàm xử lý từ module ingestion, observability, retrieval và evaluation. Đầu ra chính là `data/results/baseline_metrics.json` và `data/reports/phase1_report.md`; ngoài ra luồng còn tạo dữ liệu sạch, test set, quality report, freshness report, ChromaDB collection và file câu trả lời chi tiết. Tôi phụ trách việc kết nối và xuất kết quả baseline, không nhận là người viết toàn bộ logic bên trong các module thành phần.

## 3. Cách tôi triển khai baseline

Trong `main()` của `phase1.py`, tôi sắp các bước theo thứ tự phụ thuộc dữ liệu. Pipeline lấy bản ghi nguồn trước, sau đó gọi `build_clean_dataframe()` và lưu cả CSV lẫn JSON. Trên dataframe sạch, pipeline chạy `run_data_quality_checks()` để ghi lại chất lượng dữ liệu và freshness. Tiếp theo, `LocalEmbeddingIndex.build()` tạo collection `papers-baseline` từ nội dung đã chuẩn hóa.

Pipeline chỉ tạo lại test set khi file chưa tồn tại hoặc khi bật `REFRESH_TEST_SET`. Cách này giúp dùng cùng bộ câu hỏi cho các lần đánh giá sau. Sau khi gọi `evaluate_pipeline()`, pipeline gọi `generate_phase1_report()` từ `src/observability/reporting.py` với `quality_report` cùng `evaluation.summary` của đúng lần chạy đó. Báo cáo trình bày số bài báo sạch, tên collection, trạng thái quality/freshness và các chỉ số đánh giá. Bản sửa sau review đã chuyển logic tạo Markdown sang module reporting chung và nối vào pipeline (trước review logic này từng nằm trong `phase1.py`).

Một điểm cần chú ý là pipeline baseline dừng lại (raise lỗi) nếu quality/freshness không đạt, không tạo index trên dữ liệu lỗi. Vì vậy metrics tốt luôn đi cùng quality đạt chuẩn; metrics tốt không đủ để kết luận nếu đọc tách rời tín hiệu quality trong báo cáo.

## 4. Kết quả và cách đối chiếu

Các artifact hiện có cho thấy baseline xử lý **24 bài báo sạch** và tạo collection `papers-baseline`. Quality gate và freshness đều có trạng thái `True`; trong 24 bài có 1 bài quá ngưỡng 180 ngày, tương ứng tỷ lệ khoảng **4,17%**, thấp hơn ngưỡng tối đa 25%.

Trên bộ đánh giá 10 câu (lần verify 2026-09-26, grounded LLM với provider Gemini thật, judge heuristic tường minh), `retrieval_hit_rate = 1.0` và `mean_token_f1 = 0.8728`. `judge_accuracy = 1.0`, `mean_judge_score = 4.4`. Đây là kết quả của bộ test hiện tại, không phải khẳng định hệ thống sẽ đạt tuyệt đối với mọi câu hỏi. Ragas được cấu hình bỏ qua khi chưa bật `RUN_RAGAS=1`.

| Nội dung kiểm tra | Bằng chứng |
|---|---|
| Số bài, collection và tóm tắt kết quả | `data/reports/phase1_report.md` |
| Metrics trên 10 câu hỏi | `data/results/baseline_metrics.json` |
| Câu trả lời và tài liệu truy xuất của từng câu | `data/results/baseline_answers.json` |
| Kết quả GX và freshness | `data/quality/baseline_quality_report.json`, `data/quality/baseline_freshness_report.json` |
| Bộ câu hỏi dùng để đánh giá | `data/eval/test_set.json` |

Lệnh chạy baseline là:

```bash
python script/run_phase1.py
```

Các file kết quả ở trên đã có trong repository và khớp với nhau. Ngày 2026-09-26 đã chạy lại baseline trên venv Python 3.12.10 (`python script/run_phase1.py`, exit code 0) trong khuôn khổ `script/verify_submission.cmd`, nên artifact hiện tại chính là log của lần chạy trên phiên bản nộp bài.

## 5. Quyết định kỹ thuật và giới hạn

Tôi chọn gom phần điều phối trong `main()` và tạo nội dung report từ chính `quality_report` cùng `evaluation.summary` của lần chạy đó. Nhờ vậy, số liệu trong báo cáo được lấy từ kết quả pipeline thay vì nhập tay. Việc giữ test set hiện có cũng giúp so sánh baseline với corrupted và repaired trên cùng câu hỏi.

Giới hạn hiện tại là các chỉ số đánh giá dựa trên 10 câu hỏi, nên cần mở rộng test set và kiểm tra trên câu hỏi không chứa nguyên văn tên bài báo để đo khả năng truy xuất tổng quát hơn. (Việc chuyển logic tạo Markdown sang module reporting — cải tiến từng dự định ở đây — đã được thực hiện trong bản sửa sau review.)

## 6. Hiểu biết của tôi về luồng chung

Dữ liệu từ Crossref được lưu thành raw artifact để có thể truy vết nguồn. Bước cleaning chuẩn hóa văn bản, tính tuổi bài báo và tạo `text_for_embedding`; bước indexing dùng trường này để tạo vector trong ChromaDB. Test set lưu câu hỏi, câu trả lời chuẩn và `ground_truth_doc_ids`. Khi đánh giá, pipeline đối chiếu ID tài liệu truy xuất với ID chuẩn để tính hit rate và so sánh câu trả lời với đáp án để tính Token F1.

Quality checks kiểm tra tính đầy đủ, duy nhất và độ dài của dữ liệu; freshness kiểm tra tỷ lệ bài báo quá 180 ngày. Sau khi cố ý làm bẩn dữ liệu, việc giữ nguyên test set giúp mức thay đổi của metrics có cơ sở so sánh. Lần verify 2026-09-26 ghi nhận hit rate **1.0 → 0.8 → 1.0**, Token F1 **0.8728 → 0.6792 → 0.8572**, judge accuracy **1.0 → 0.7 → 0.9** qua ba trạng thái baseline, corrupted và repaired. Phần repair do luồng khác thực hiện; tôi dùng các kết quả này để hiểu vai trò của baseline làm mốc so sánh.

## 7. Tự đánh giá đóng góp

Đóng góp chính của tôi là biến các module riêng lẻ thành một quy trình baseline có thứ tự rõ ràng và xuất kết quả có thể đối chiếu bằng file. Qua phần việc này, tôi hiểu rằng một báo cáo có giá trị khi số liệu đi thẳng từ artifact của cùng lần chạy, và một chỉ số RAG cao vẫn cần được đọc cùng tín hiệu chất lượng dữ liệu. Lần chạy lại baseline ngày 2026-09-26 đã xác nhận khả năng tái hiện trên phiên bản cuối; trước khi nộp, tôi sẽ kiểm tra lịch sử commit tương ứng.
