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

Pipeline chỉ tạo lại test set khi file chưa tồn tại hoặc khi bật `REFRESH_TEST_SET`. Cách này giúp dùng cùng bộ câu hỏi cho các lần đánh giá sau. Sau khi gọi `evaluate_pipeline()`, tôi lấy metrics để tạo báo cáo Markdown bằng `_build_report()` ngay trong `phase1.py`. Báo cáo trình bày số bài báo sạch, tên collection, trạng thái quality/freshness và các chỉ số đánh giá. Hàm `generate_phase1_report()` trong `src/observability/reporting.py` hiện vẫn là hàm mẫu chưa triển khai; luồng baseline không gọi hàm đó.

Một điểm cần chú ý là bước kiểm tra chất lượng ghi nhận trạng thái đạt hay không đạt, còn pipeline baseline vẫn tiếp tục tạo index và đánh giá. Vì vậy trạng thái quality trong báo cáo cần được đọc cùng metrics; metrics tốt không đủ để kết luận dữ liệu luôn đạt chuẩn.

## 4. Kết quả và cách đối chiếu

Các artifact hiện có cho thấy baseline xử lý **24 bài báo sạch** và tạo collection `papers-baseline`. Quality gate và freshness đều có trạng thái `True`; trong 24 bài có 1 bài quá ngưỡng 180 ngày, tương ứng tỷ lệ khoảng **4,17%**, thấp hơn ngưỡng tối đa 25%.

Trên bộ đánh giá 10 câu, `retrieval_hit_rate = 1.0` và `mean_token_f1 = 1.0`. `judge_accuracy = 1.0`, `mean_judge_score = 5`. Đây là kết quả của bộ test hiện tại, không phải khẳng định hệ thống sẽ đạt tuyệt đối với mọi câu hỏi. Ragas được cấu hình bỏ qua khi chưa bật `RUN_RAGAS=1`.

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

Các file kết quả ở trên đã có trong repository và khớp với nhau. Tôi chưa ghi nhận log của một lần chạy lại trên môi trường nộp bài, nên trước khi nộp cần chạy lệnh này và kiểm tra exit code cùng thời điểm cập nhật artifact.

## 5. Quyết định kỹ thuật và giới hạn

Tôi chọn gom phần điều phối trong `main()` và tạo nội dung report từ chính `quality_report` cùng `evaluation.summary` của lần chạy đó. Nhờ vậy, số liệu trong báo cáo được lấy từ kết quả pipeline thay vì nhập tay. Việc giữ test set hiện có cũng giúp so sánh baseline với corrupted và repaired trên cùng câu hỏi.

Giới hạn hiện tại là phần báo cáo pha 1 nằm trong `phase1.py`, trong khi module `observability/reporting.py` vẫn có hàm `generate_phase1_report()` chưa hoàn thiện. Nếu tiếp tục cải thiện, tôi sẽ chuyển logic tạo Markdown sang module reporting, gọi từ pipeline và kiểm tra rằng nội dung report vẫn khớp JSON metrics. Ngoài ra, các chỉ số đánh giá hiện dựa trên 10 câu hỏi, nên cần mở rộng test set và kiểm tra trên câu hỏi không chứa nguyên văn tên bài báo để đo khả năng truy xuất tổng quát hơn.

## 6. Hiểu biết của tôi về luồng chung

Dữ liệu từ Crossref được lưu thành raw artifact để có thể truy vết nguồn. Bước cleaning chuẩn hóa văn bản, tính tuổi bài báo và tạo `text_for_embedding`; bước indexing dùng trường này để tạo vector trong ChromaDB. Test set lưu câu hỏi, câu trả lời chuẩn và `ground_truth_doc_ids`. Khi đánh giá, pipeline đối chiếu ID tài liệu truy xuất với ID chuẩn để tính hit rate và so sánh câu trả lời với đáp án để tính Token F1.

Quality checks kiểm tra tính đầy đủ, duy nhất và độ dài của dữ liệu; freshness kiểm tra tỷ lệ bài báo quá 180 ngày. Sau khi cố ý làm bẩn dữ liệu, việc giữ nguyên test set giúp mức thay đổi của metrics có cơ sở so sánh. Các artifact hiện có ghi nhận hit rate **1.0 → 0.8 → 1.0** và Token F1 **1.0 → 0.9 → 1.0** qua ba trạng thái baseline, corrupted và repaired. Phần repair do luồng khác thực hiện; tôi dùng các kết quả này để hiểu vai trò của baseline làm mốc so sánh.

## 7. Tự đánh giá đóng góp

Đóng góp chính của tôi là biến các module riêng lẻ thành một quy trình baseline có thứ tự rõ ràng và xuất kết quả có thể đối chiếu bằng file. Qua phần việc này, tôi hiểu rằng một báo cáo có giá trị khi số liệu đi thẳng từ artifact của cùng lần chạy, và một chỉ số RAG cao vẫn cần được đọc cùng tín hiệu chất lượng dữ liệu. Trước khi nộp, tôi sẽ kiểm tra lịch sử commit tương ứng và chạy lại baseline để xác nhận khả năng tái hiện trên phiên bản cuối.
