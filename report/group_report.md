# Group Report — BLS — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

- Khóa/lớp: K4-L3B; nhóm: BLS; ngày cập nhật: 2026-09-26.
- Repository: https://github.com/foxxiee04/K4-L3B-DAY10-BLS-DataPipelineDataObservability
- Trạng thái: đã verify end-to-end bản sửa sau review trên venv Python 3.12.10 (baseline → corruption → repair, exit code 0) và demo agent provider thật thành công ngày 2026-09-26.

| Thành viên | MSSV | Phần việc chính |
| --- | --- | --- |
| Đinh Tuấn Long | 2A202602620 | Dữ liệu ban đầu: ingestion, cleaning, lưu dữ liệu, quality/freshness |
| Lê Duy Bảo | 2A202602749 | Benchmark test set |
| Trần Quốc Sáng | 2A202602712 | Baseline orchestration và báo cáo pha 1 |
| Nguyễn Đình Anh Đức | 2A202602856 | Corruption, repair, orchestration và báo cáo so sánh |

Phân công và commit đối chiếu tại [TEAM.md](../docs/TEAM.md). Những phần retrieval có sẵn trong starter không được tự nhận là toàn bộ đóng góp của một thành viên.

## 2. Tóm tắt kết quả

Nhóm BLS xây dựng pipeline dữ liệu cho bài toán hỏi đáp trên metadata Crossref. Dữ liệu được lưu raw, chuẩn hóa thành 24 bản ghi sạch, kiểm tra bằng Great Expectations 1.x và freshness SLA, sau đó tạo vector MiniLM trong ChromaDB. Bộ benchmark gồm 10 câu thuộc bốn nhóm nghiệp vụ và được giữ nguyên qua ba trạng thái. Nhóm triển khai sáu lỗi dữ liệu, lưu log, đánh giá lại và phục hồi từ raw snapshot. Kết quả verify bản cuối (evaluation_contract v2, semantic_only, grounded_llm, judge heuristic thống nhất ba pha): hit rate 1.0 → 0.8 → 1.0, Token F1 0.8728 → 0.6792 → 0.8572, judge accuracy 1.0 → 0.7 → 0.9, mean judge score 4.4 → 3.6 → 4.2; quality và freshness lần lượt True → False → True. Dữ liệu repaired trùng baseline (hash JSON/CSV giống hệt).

Review phát hiện benchmark cũ chèn exact-title lookup và trích đáp án từ metadata, đồng thời baseline dùng heuristic judge fallback khác hai pha sau. Bản sửa đã bỏ việc chèn kết quả exact lookup, dùng LLM trả lời có context khi chọn provider thật, quy định judge rõ ràng và kiểm tra cấu hình/test set trước khi so sánh. Đường dẫn tải Chroma và hàm reporting cũng được sửa. Ngày 2026-09-26 nhóm đã chạy lại end-to-end bản sửa trên venv Python 3.12.10 đang hoạt động (xem mục 4 và 10). Số liệu lịch sử của bản cũ (F1 1.0 → 0.9 → 1.0, dùng exact-title lookup và judge không đồng nhất) chỉ còn giá trị tham khảo, không dùng làm kết quả nghiệm thu.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref API / snapshot → PaperRecord → cleaning → quality + freshness
→ MiniLM → ChromaDB baseline → test set → evaluation + baseline report
→ six corruptions → corrupted index → same test set → evaluation
→ repair from raw → repaired index → same test set → comparison report
```

| Khối | Input | Output | Owner |
| --- | --- | --- | --- |
| Ingestion/cleaning | Crossref metadata, run_date | Raw JSON, clean CSV/JSON | Long |
| Quality/freshness | Clean/corrupted/repaired DataFrame | JSON kiểm định | Long |
| Test set | Clean DataFrame | 10 câu và ground truth | Bảo |
| Baseline integration | Các module và Settings | Index, metrics, report | Sáng |
| Corruption/repair | Baseline và raw snapshot | Log, hai index, metrics, comparison | Đức |

## 4. Cách tái hiện kết quả

Python yêu cầu >=3.11,<3.14. Trong CMD tại repo, kích hoạt venv và cài project:

```cmd
.venv\Scripts\activate.bat
python -m pip install -e .
```

Cấu hình `.env` từ `.env.example`, không đưa secret vào Git. `LLM_PROVIDER=gemini` hoặc alias `google` dùng Gemini; các provider khác gồm openai, anthropic, openrouter, ollama và custom. Model phải phù hợp provider.

Để kiểm tra offline có thể đặt:

```cmd
set LLM_PROVIDER=mock
set JUDGE_MODE=heuristic
set REFRESH_SOURCE=false
script\verify_submission.cmd
```

Mock chỉ là QA trích xuất, không chứng minh LLM. Để nghiệm thu provider thật, mở CMD đã kích hoạt venv, bỏ override mock bằng `set LLM_PROVIDER=` và dùng `.env` đã điền provider/model/key:

```cmd
set JUDGE_MODE=heuristic
script\verify_submission.cmd
python script/run_agent_demo.py
```

Nếu muốn LLM judge, đặt `JUDGE_MODE=llm` rồi chạy lại cả hai pipeline; lỗi judge sẽ dừng thay vì âm thầm fallback. Giữ nguyên cấu hình giữa các pha. Demo ghi `data/results/agent_demo_answers.json` gồm câu trả lời và bằng chứng gọi tool.

Lần verify cuối dùng Python 3.12.10, `LLM_PROVIDER=gemini`, model thật `gemini-3.5-flash-lite` (họ model 2.5 đã bị API ngừng phục vụ với key này nên không dùng được), `JUDGE_MODE=heuristic`. Lưu ý môi trường cục bộ: máy chạy verify phải ghim `pyarrow==21.0.0` vì binary pyarrow 25.0.1 bị Windows Application Control chặn load — đây là workaround của máy, không phải yêu cầu lab, và không đổi ràng buộc dependency của project.

| Lệnh | Trạng thái xác minh trong lần review |
| --- | --- |
| Quality/cleaning riêng | Người dùng đã cung cấp terminal pass |
| `run_phase1.py` | Đã chạy lại 2026-09-26, exit code 0, metrics có evaluation_contract |
| `run_corruption_flow.py` | Đã chạy lại 2026-09-26, exit code 0, bảng 3 trạng thái đầy đủ |
| `run_agent_demo.py` | Đã chạy với Gemini thật (`gemini-3.5-flash-lite`); agent gọi tool `lookup_paper`, answer grounded theo tool output |

## 5. Ingestion, cleaning và data contract

- Crossref `/works`, query từ Settings; filter có abstract và khoảng ngày được cấu hình.
- Snapshot offline chứa 24 bài. Không suy diễn snapshot là kết quả tải API thật trong lần chạy này.
- Raw giữ `crossref_response.json` và `crossref_records.json`; refresh có timeout, retry hữu hạn và fallback.
- PaperRecord gồm paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url, comment.
- Cleaning chuẩn hóa text/list, loại dòng thiếu ID/title/summary/ngày hợp lệ, deduplicate theo paper_id giữ updated mới nhất.
- Bổ sung age_days, authors_joined, categories_joined, summary_chars và text_for_embedding 5 phần.
- Ngày xuất bản giữ dạng ISO; không thay ngày để vượt qua freshness. Dữ liệu stale vẫn được giữ để kiểm định.

## 6. Evaluation setup

| Thành phần | Thiết lập |
| --- | --- |
| Test set | `data/eval/test_set.json`, 10 câu: summary 3, authors 3, date 2, categories 2 |
| Ground truth | Nội dung chuẩn và paper_id từ clean baseline |
| Embedding | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store | ChromaDB, ba collection papers-baseline/corrupted/repaired |
| Top-k | 4 |
| QA mới | Semantic retrieval; LLM trả lời từ context, hoặc extractive mock khi chọn mock |
| Judge mới | `JUDGE_MODE=heuristic` hoặc `llm`; không tự chuyển mode khi lỗi |
| Tính so sánh | Hash test set, provider/model, judge, embedding và top-k được ghi trong evaluation_contract |

## 7. Kết quả baseline

Kết quả verify 2026-09-26: 24 clean records; ChromaDB có papers-baseline 24 tài liệu; 10 câu đánh giá; hit rate=1.0, Token F1=0.8728, judge accuracy=1.0, mean judge score=4.4 (grounded LLM, judge heuristic tường minh, contract v2, không fallback âm thầm). Artifact lịch sử của bản cũ ghi hit rate=1.0, Token F1=1.0 kèm heuristic fallback không đồng nhất — chỉ còn giá trị tham khảo. Ragas bỏ qua theo cấu hình mặc định.

Raw, clean, manifests, test set, quality, answers, metrics và report đều có trong repo. Không sửa tay metrics để tạo kết quả cho code mới. Sau khi chạy lại, xem `data/results/baseline_metrics.json` và `data/reports/phase1_report.md` làm nguồn chính.

## 8. Data quality và freshness

GX 1.x ephemeral context kiểm tra số dòng, not-null, paper_id unique, độ dài và nội dung không chỉ có khoảng trắng. Số dòng kỳ vọng là max_results=24; title tối thiểu 8 ký tự, summary tối thiểu 50 ký tự. Các ngưỡng độ dài được nhóm chọn cho lab.

Freshness kiểm tra age_days >180; tỷ lệ stale >25% không đạt. Tỷ lệ đúng 25% vẫn đạt nếu ngày/tuổi hợp lệ. Dữ liệu rỗng hoặc tuổi không hợp lệ không được coi là fresh. Baseline lịch sử có 1/24 bài stale, khoảng 4.17%.

Baseline mới dừng trước khi tạo index nếu quality/freshness không đạt. Corruption flow vẫn cố ý index dữ liệu lỗi để đo tác động trong thí nghiệm.

## 9. Corruption scenarios và repair

| Lỗi | Thao tác trên dataset 24 bài | Bằng chứng |
| --- | --- | --- |
| Drop latest | Bỏ 5 bài mới nhất (ceil 20%) | Log paper_ids |
| Blank summary | Xóa summary 2 bài | Summary rỗng, quality fail |
| Inject noise | Thêm chuỗi rác vào 2 bài | Log và embedding text |
| Truncate title | Cắt title 2 bài xuống 7 ký tự | Length expectation fail |
| Stale date | Lùi 6 bài 365 ngày, cập nhật age_days | 6/21 stale sau duplicate |
| Duplicate | Nhân bản 2 dòng giữ paper_id | Unique expectation fail |

Corruption rebuild text_for_embedding để index thật sự nhận dữ liệu lỗi. Repair đọc raw snapshot, cleaning lại, lưu riêng dữ liệu repaired, xây lại collection và đánh giá. Cùng raw và run_date cho đầu ra cleaning xác định; không sửa metric hoặc vá dataframe corrupted để giả lập phục hồi.

## 10. So sánh baseline, corrupted và repaired

**Bảng kết quả verify bản cuối (2026-09-26, nguồn chính `data/reports/corruption_report.md`).**

| Metric/signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0 | 0.8 | 1.0 |
| mean_token_f1 | 0.8728 | 0.6792 | 0.8572 |
| judge_accuracy | 1.0 | 0.7 | 0.9 |
| mean_judge_score | 4.4 | 3.6 | 4.2 |
| Quality/freshness | True/True | False/False | True/True |
| Rows | 24 | 21 | 24 |

Corruption → số dòng/unique/độ dài/freshness vi phạm → retrieval hit giảm 0.2 và Token F1 giảm 0.1936. Repair từ raw → dữ liệu sạch và quality/freshness phục hồi → hit rate về lại 1.0 hoàn toàn; Token F1 phục hồi 0.8572, gần baseline 0.8728 (chênh lệch nhỏ do LLM sinh câu trả lời khác nhau giữa các lần chạy). Chưa tách riêng tác động từng corruption; judge đã thống nhất heuristic ở cả ba pha nên judge metrics so sánh được trực tiếp.

Xác nhận demo provider thật (2026-09-26): `python script/run_agent_demo.py` chạy với provider Gemini, model `gemini-3.5-flash-lite`; agent gọi tool `lookup_paper` và trả lời grounded theo tool output; evidence lưu tại `data/results/agent_demo_answers.json`. Đây là model thật đã gọi được API trong lần demo cuối, không phải yêu cầu bắt buộc của lab.

## 11. Vấn đề tích hợp quan trọng

Manifest chứa đường dẫn máy tác giả làm loader không portable. Đã đổi loader dùng settings.paths.chroma_dir và manifest mới lưu đường dẫn tương đối. Bản cũ còn có baseline judge fallback và exact-title injection; đã chuyển benchmark sang semantic retrieval, judge mode tường minh, lưu evaluation_contract và từ chối baseline cũ/khác cấu hình. Reporting pha 1 đã được triển khai trong module chung và nối vào pipeline.

## 12. Giới hạn và hướng cải thiện

- Đã chạy lại end-to-end bản sửa (`script/verify_submission.cmd` exit code 0 trên venv hoạt động) và demo provider thật thành công; giữ đầu mục này để nhắc kiểm tra lại nếu code còn thay đổi trước giờ nộp.
- Test set 10 câu có tiêu đề nguyên văn: cần thêm câu paraphrase để đo tổng quát hóa.
- Heuristic judge không phải LLM judge; chọn chế độ thống nhất và ghi rõ trong báo cáo.
- Corruption áp dụng đồng thời: cần ablation từng lỗi để phân tích nhân quả riêng.
- Báo cáo cá nhân đã được đối chiếu với metrics verify 2026-09-26; từng tác giả đọc lại phần của mình và tự đánh dấu cam kết trước khi nộp.
- Không khẳng định đạt bonus test coverage/auto-repair/dashboard khi chưa có bằng chứng.

## 13. Checklist trước khi nộp

Trạng thái kỹ thuật từng checkpoint (verify 2026-09-26, venv Python 3.12.10):

| Checkpoint | Trạng thái kỹ thuật | Bằng chứng |
| --- | --- | --- |
| CP0 | Hoàn thành | 24 records, 2 raw JSON, `.env` hợp lệ |
| CP1 | Hoàn thành | Clean 24 dòng, GX success=True, freshness True |
| CP2 | Hoàn thành | Test set 10 câu (3-3-2-2), collection `papers-baseline` 24 docs |
| CP3 | Hoàn thành | `baseline_metrics.json` có contract, `phase1_report.md` |
| CP4 | Hoàn thành | 6 corruptions, `corruption_log.json`, metrics suy giảm rõ |
| CP5 | Hoàn thành | `repaired_metrics.json`, `corruption_report.md` đủ bảng 3 trạng thái |
| CP6 | Kỹ thuật demo xong; còn thủ công | Verify + agent demo thành công; chờ commit/push, Contributors, nộp LMS |

- [x] Điền thông tin BLS và phạm vi đóng góp từ dữ liệu có sẵn.
- [x] Đối chiếu metrics verify mới với answers và test set.
- [x] Ghi rõ giới hạn judge và phiên bản đánh giá.
- [x] Chạy lại baseline và corruption flow bằng code cuối, cả hai exit code 0 (xong 2026-09-26).
- [x] Chạy demo LLM Agent, kiểm tra tool evidence và cập nhật kết quả cuối (xong 2026-09-26).
- [ ] Mỗi thành viên đọc lại báo cáo cá nhân và tự đánh dấu cam kết.
- [ ] Kiểm tra Contributors, secret trong Git history và mỗi người nộp link LMS.
