# Báo cáo cá nhân — K3 Day 09 Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Lương Đăng Doanh |
| MSSV | 2A202601209 |
| Khóa/Lớp | K3 — E403 |
| Vai trò chính | Coordinator, policy integration và verification |
| Ngày hoàn thành | 2026-08-05 |

Thông tin họ tên/MSSV được suy ra từ tên workspace và repo `K3-Day9-Multi-Agent-A2A-01209`; lớp E403 được xác nhận từ breakdown web của mã 01209.

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Coordinator và A2A handoff | `coordinator.py`, `tracing.py`, `contracts.py` | 50 case + domain findings | Output, trace, metadata | Hoàn thành |
| Policy integration | `agents/policy.py`, `config.py` | Order/payment/delivery findings | ResolutionCandidate | Hoàn thành |
| Independent verification | `agents/verifier.py`, `validation.py` | Candidate + CSV rows | VerificationReport | Hoàn thành |
| Local grader và packaging | `local_grader.py`, `cli.py` | 50 output | Component score + ZIP | Hoàn thành |
| Tài liệu kiến trúc/runbook | `architecture.md`, `RUNBOOK.md`, `GRADER_ANALYSIS.md` | Code và kết quả run thật | Tài liệu tái lập | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
|---|---|---|
| Audit dữ liệu Olist | Order/Seller, Payment, Delivery | Xác nhận join, 50 order tồn tại, zero missing FK trong tập case |
| Reverse-engineer phần công khai của web grader | Local grader | Xác nhận weights 20/20/15/15/20/10 và giới hạn ZIP; không truy cập secret/answer key |
| Kiểm soát secret/model | Optional LLM audit | `.env` gitignored; model name nằm trong source/metadata |

## 3. Kết quả theo vai trò

| Nhiệm vụ | Artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| Chạy end-to-end | `output/EC_001..EC_050.json` | 50/50 output | `python -m dispute_agents.cli run` |
| Verify schema và nghiệp vụ | `logging/trace.jsonl` | 50 Verifier PASS trước write | Parse trace, kiểm `VerificationReport` và `write` |
| Chấm local | Local grader | 100.0, 0 hard gate, sáu component 100 | `python -m dispute_agents.cli grade` |
| Chấm web | N7 Competition, E403/01209 | 100.0, 0 hard gate, sáu component 100 | Breakdown lúc 2026-08-05T03:55:01Z |
| Trace latest run | `logging/trace.jsonl` | 550 event ở run không dùng LLM | Đếm JSONL và validate JSON từng dòng |
| Metadata tái lập | `logging/metadata.json` | runtime/model/checksum/counts | Parse JSON và đối chiếu source |

Phân bố issue từ run thật: canceled 8, unavailable 8, late seller 8, late logistics 8, valid split 9, unsupported late claim 9. Trường hợp unavailable không có item được giữ `item_ids=[]`, `seller_ids=[]`, item/freight total bằng 0.

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Một customer claim không đủ để quyết định hoàn tiền. Pipeline phải tổng hợp order status, item/seller shipping limit, carrier/customer timestamps và mọi payment row; sau đó áp policy precedence, tạo evidence có thể resolve và kiểm lại toàn bộ trước khi ghi.

### Cách triển khai

Coordinator không làm thay domain agent. OrderSeller Agent tổng hợp items độc lập; Payment Agent aggregate payment theo order để tránh Cartesian product; Delivery Agent phân biệt seller handoff-late với logistics-late; Policy Agent chỉ nhận typed findings và không đọc CSV. Verifier dùng đường tính độc lập, re-query cùng source rows và so exact sáu component.

Tiền được parse từ chuỗi CSV bằng `Decimal` và quantize `0.01`. Payment được coi reconciled khi `abs(payment_total - (item_total + freight_total)) <= 0.10`. Datetime dùng giá trị trong CSV và strict `>`; bằng deadline không phải late.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `schemas/input.schema.json`; `EC_001..EC_050`; `claimed_order_id` là join key |
| Output | `schemas/output.schema.json`; đúng bảy top-level fields README |
| Module phụ thuộc | Repository read-only, typed dataclasses, policy config |
| Module sử dụng output | Verifier, local grader, ZIP packager |
| Điều kiện lỗi | Missing order, schema mismatch, invalid evidence, no policy match, math/action/refund mismatch |

### Cách xác minh

```powershell
$env:PYTHONPATH = "src"
python -m dispute_agents.cli run
python -m pytest
python -m dispute_agents.cli grade
```

- Kết quả mong đợi: 50 output, 0 hard gate, local score 100.0.
- Kết quả thực tế: đạt đúng kỳ vọng ở lần chạy E2E đã ghi trong metadata/trace.
- Artifact: `output/`, `logging/trace.jsonl`, `logging/metadata.json`; không artifact nào chứa secret.

## 5. Quyết định kỹ thuật quan trọng

- Bối cảnh: LLM có thể diễn giải tốt nhưng dễ tạo evidence/timestamp/refund không tồn tại, trong khi policy README hoàn toàn xác định.
- Phương án cân nhắc: (1) một prompt lớn sinh toàn bộ output; (2) nhiều LLM agent tự do; (3) typed deterministic domain agents + optional LLM audit.
- Phương án chọn: (3).
- Lý do: deterministic path tái lập, phép tính chính xác, access control rõ và verifier độc lập; vẫn giữ integration `gpt-4o-mini` cho audit có structured schema khi có API key.
- Bằng chứng: hai lần chạy có output checksum giống nhau; local oracle exact đạt 100.0 ở sáu component.

## 6. Một lỗi hoặc blocker đã xử lý

Repo starter không có 50 input, chỉ có `.gitkeep`. Bộ input được xác định từ nhiều fork công khai, sau đó so toàn bộ Git blob SHA giữa hai nguồn trước khi import. Không đọc hoặc sao chép output của đội khác. Sau import, tất cả 50 filename/case_id/order ID unique và order đều resolve trong CSV.

Blocker thứ hai là web frontend không chứa code scorer phía server. Thay vì tuyên bố đã clone exact grader, local grader được viết theo README + CSV oracle và ghi disclaimer rõ về private partial scoring/hard gates.

## 7. Hiểu biết end-to-end

1. Input được validate exact schema và filename/case_id.
2. Coordinator gửi CaseEnvelope; OrderSeller trả items, sellers, item/freight total.
3. Payment nhận expected total qua handoff và aggregate mọi payment row.
4. Delivery so customer delivery với estimate và carrier handoff với từng item limit.
5. Policy áp precedence canceled → unavailable → seller late → logistics late → split → unsupported.
6. Coordinator dựng entity/evidence canonical; Verifier re-query và so exact issue/root/party/money/action.
7. Chỉ candidate PASS mới atomic-write output; latest trace được overwrite và metadata ghi checksum.
8. Packager chỉ nhận đúng 50 output và giữ đúng đường dẫn `output/EC_001.json` đến `output/EC_050.json` trong ZIP.

Phân biệt trách nhiệm late delivery: nếu carrier nhận hàng sau item `shipping_limit_date`, seller chịu trách nhiệm; nếu carrier nhận đúng hạn nhưng giao khách sau estimate, logistics chịu trách nhiệm. Split payment chỉ hợp lệ khi có ít nhất hai payment row và tổng payment khớp tổng item + freight trong tolerance.

## 8. Rủi ro và giới hạn

- README không định nghĩa công thức confidence; feedback web cho thấy 1.0 đạt assessment cao hơn 0.92 nên pipeline giữ 1.0 khi verifier xác nhận đầy đủ.
- Exact source code server hard-gate/partial scorer không công khai, nhưng artifact cuối đã được web grader xác nhận 100.0 với 0 hard gate.
- OpenAI không công bố số tham số `gpt-4o-mini`; không thể chứng minh giới hạn ≤10B. Metadata ghi `not_verifiable`; cần organizer xác nhận nếu bật LLM audit.
- API key thật chưa có trong workspace tại thời điểm run, vì vậy run đã xác minh dùng deterministic agents và `model.invocation_count=0`.

## 9. Tự đánh giá

- [x] 50 input/output đúng tên và schema.
- [x] Domain agents có module/handoff riêng, không phải nhiều tên quanh một prompt.
- [x] Verifier PASS trước mọi write.
- [x] Evidence resolve và tiền dùng Decimal.
- [x] Latest trace/metadata được tạo từ run thật.
- [x] Local grader đạt 100.0 và ZIP packager strict.
- [x] Web grader E403/01209 đạt 100.0 ở cả sáu component.
- [x] Lớp E403 được xác nhận từ breakdown web.
- [ ] Organizer xác nhận eligibility của `gpt-4o-mini` theo giới hạn tham số.
- [ ] Chủ repo cung cấp API key thật nếu bắt buộc chạy optional LLM audit.

Người báo cáo: Lương Đăng Doanh
Ngày: 2026-08-05
