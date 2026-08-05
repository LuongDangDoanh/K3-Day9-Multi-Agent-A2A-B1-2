# Phân tích bộ chấm K3 công khai

Ngày kiểm tra: 2026-08-05.

- Trang: <https://n7-competition.pages.dev/k3>
- API health công khai: <https://api-day09-competition.35-240-128-112.sslip.io/api/health>
- Client xác nhận file `.zip` tối đa 5 MiB và cooldown 120 giây.
- Breakdown công khai có sáu component: assessment, entities, root, evidence, financial, actions.
- Trọng số khớp README: 20%, 20%, 15%, 15%, 20%, 10%.
- Bundle frontend chỉ có UI/API client; không có source code scorer, answer key hay exact hard-gate implementation.

Vì vậy `dispute_agents.local_grader` là bản tái lập hợp pháp theo đặc tả: strict schema gate, re-query CSV, policy precedence, evidence resolution và exact component comparison. Nó cố ý không hard-code 50 đáp án.

Theo yêu cầu submission đã được xác nhận, ZIP phải chứa đúng `output/EC_001.json` đến `output/EC_050.json`, không có file bổ sung.

## Kết quả web đã xác minh

Submission `E403/01209` lúc `2026-08-05T03:55:01Z` đạt **100.0**, `hard_gate_count=0`; cả assessment, entities, root, evidence, financial và actions đều 100.0.

Feedback-controlled audit xác định quy tắc còn thiếu: evidence `seller:<id>` chỉ hợp lệ cho `late_delivery_seller`. Với các issue khác, seller có thể tồn tại trong affected entities nhưng không phải bằng chứng trực tiếp của root cause và bị tính false positive nếu đưa vào `evidence_ids`.
