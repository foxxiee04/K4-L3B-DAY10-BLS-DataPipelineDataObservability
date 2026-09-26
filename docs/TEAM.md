# Danh sách thành viên & phân công — BLS

- Nhóm: **BLS**
- Lớp/bài: **K4-L3B-DAY10**
- Repository: https://github.com/foxxiee04/K4-L3B-DAY10-BLS-DataPipelineDataObservability

Phân công đối chiếu báo cáo cá nhân và lịch sử Git. Không gán chức danh trưởng nhóm khi chưa có xác nhận.

| Họ và tên | MSSV | Email tác giả Git | Phạm vi chính | Báo cáo cá nhân |
| --- | --- | --- | --- | --- |
| Đinh Tuấn Long | 2A202602620 | dinhtuanlong05@gmail.com | CP0–CP1: ingestion, cleaning, lưu dữ liệu, GX và freshness | [Báo cáo](../report/2A202602620_DinhTuanLong.md) |
| Lê Duy Bảo | 2A202602749 | leduybao612003@gmail.com | CP2: benchmark test set | [Báo cáo](../report/LeDuyBao_2A202602749.md) |
| Trần Quốc Sáng | 2A202602712 | sangtranquocgl@gmail.com | CP3: tích hợp baseline, indexing/evaluation, báo cáo pha 1 | [Báo cáo](../report/individual_2A202602712_TranQuocSang.md) |
| Nguyễn Đình Anh Đức | 2A202602856 | ducnda0212@gmail.com | CP4–CP5: corruption, repair, báo cáo so sánh | [Báo cáo](../report/individual_2A202602856_NguyenDinhAnhDuc.md) |

## Đóng góp có bằng chứng

### Đinh Tuấn Long — 2A202602620

- Commit `b6f083d`: ingestion, cleaning, quality/freshness, raw records và quality artifacts.
- Terminal cá nhân xác nhận Python 3.12.10, Quality=True, Freshness=True, Overall=True.
- Hỗ trợ review tích hợp và hoàn thiện tài liệu/code với AI; verify end-to-end bản cuối đã chạy thành công ngày 2026-09-26 (baseline → corruption → repair, exit code 0) cùng demo agent Gemini thật.

### Lê Duy Bảo — 2A202602749

- Commit `036c6cb`: 10 câu hỏi gồm 3 summary, 3 authors, 2 date, 2 categories.
- Bàn giao question, ground_truth và ground_truth_doc_ids dùng chung cho ba trạng thái.

### Trần Quốc Sáng — 2A202602712

- Commit `a24a50c`, `d9daa97`: tích hợp baseline và báo cáo pha 1.
- Điều phối nguồn → cleaning → quality → ChromaDB → test set → evaluation → report.
- Chuyển reporting sang module chung được bổ sung sau review; không thay đổi ghi nhận đóng góp baseline ban đầu.

### Nguyễn Đình Anh Đức — 2A202602856

- Commit `3d21d57` và báo cáo cá nhân: sáu kịch bản corruption, repair từ raw và báo cáo so sánh.
- Bàn giao corrupted/repaired metrics, answers, quality và data artifacts.

## Nghiệm thu

- Verify kỹ thuật hoàn tất 2026-09-26: 7/7 regression tests PASS; `script/verify_submission.cmd` exit code 0; metrics ba trạng thái có evaluation_contract thống nhất; demo agent Gemini (`gemini-3.5-flash-lite`) gọi tool `lookup_paper` thành công, evidence tại `data/results/agent_demo_answers.json`.
- CP0–CP5 hoàn thành kỹ thuật; CP6 còn phần thủ công: commit/push cuối, kiểm tra Contributors, mỗi người nộp link LMS.
- CP6: cả nhóm chuẩn bị demo; mỗi người tự nộp link LMS và giải thích phần phụ trách.
- Email trên lấy từ lịch sử commit; liên kết email với GitHub và Contributors cần từng người kiểm tra.
- Báo cáo của các thành viên khác giữ nguyên tên hiện có để bảo toàn liên kết. Chủ báo cáo nên thống nhất quy ước `<MSSV>_HoTen.md` trước khi nộp.
- Cam kết do từng thành viên tự xác nhận.
