# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

## BLS — kiểm tra phiên bản sau review

Trong CMD tại repo, kích hoạt venv Python 3.12 và chạy:

```cmd
python -m pip install -e .
set JUDGE_MODE=heuristic
script\verify_submission.cmd
python script/run_agent_demo.py
```

Provider/model/key lấy từ `.env`; không gửi hoặc commit key. Demo agent cần provider thật. Muốn chạy QA offline thì đặt `LLM_PROVIDER=mock`, nhưng bỏ qua demo agent và không coi đó là bằng chứng LLM hoạt động.

Bản sửa dùng semantic retrieval và QA có context, ghi `evaluation_contract`, không âm thầm fallback judge. Cần chạy lại baseline trước corruption vì artifact cũ dùng phương pháp đánh giá khác. Metrics đang commit là **kết quả lịch sử**, không phải số đo của bản sửa. Chạy xong đọc report tự sinh trong `data/reports/` và cập nhật bảng kết quả trong báo cáo nhóm/cá nhân.

Kiểm tra hồi quy không cần dịch vụ ngoài: `python -m unittest discover -s tests -v`. Các test này dùng service doubles, không thay thế chạy end-to-end. Báo cáo nhóm ghi rõ giới hạn và trạng thái nghiệm thu.

> **Hình thức:** Teamwork | **Thời lượng:** 240 phút  
> **Lịch học (Lớp B - Ca Sáng):** Thứ 7 (26/09/2026) 09:00 – 13:00  
> ⏰ **Hạn nộp LMS:** 23:59:59 cùng ngày

---

## 🧭 Đọc gì, theo thứ tự nào?

| # | Tài liệu | Mô tả |
|:---:|---|---|
| 1️⃣ | **Codelab trên VLearn LMS** | Hướng dẫn từng bước + nộp bài (mở trên trình duyệt) |
| 2️⃣ | [CHECKPOINTS.md](docs/CHECKPOINTS.md) | Phân bổ thời gian 240 phút & deliverables từng mốc |
| 3️⃣ | [RUBRIC.md](docs/RUBRIC.md) | Tiêu chí chấm điểm (100 chuẩn + 10 bonus) |
| 4️⃣ | [SUBMISSION.md](docs/SUBMISSION.md) | Nội quy, deadline, bảo mật & checklist nộp bài |
| 5️⃣ | [TEAM.md](docs/TEAM.md) | Điền thông tin nhóm & báo cáo cá nhân |

---

## Repo có sẵn gì? (Scaffolded Baseline)

- `data/raw/` — Snapshot offline Crossref API (`crossref_response.json`)
- `src/` — Khung pipeline thu thập, embedding MiniLM, đánh giá metrics (có `TODO(student)`)
- `script/` — Entrypoints: `run_phase1.py`, `run_corruption_flow.py`

## Học viên cần làm gì?

1. Hoàn thiện **Data Quality Gate** (Great Expectations 1.x) trong `src/observability/quality.py`
2. Tích hợp **Freshness Check** (`age_days`) vào Quality Gate
3. Chạy **Baseline → Corruption → Repair** → xuất bảng đối chiếu 3 trạng thái
4. **Live Demo** trên bảng & nộp link repo lên VLearn LMS
