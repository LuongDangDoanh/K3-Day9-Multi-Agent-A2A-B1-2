# Báo cáo cá nhân — K3 Day 09 Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Trần Tuấn Trung |
| MSSV | 2A202601769 |
| Khóa/Lớp | K3 — E403 |
| Vai trò chính | CLI development, schema validation, grader implementation và packaging |
| Ngày hoàn thành | 2026-08-05 |

Thông tin họ tên/MSSV được xác định theo mã học viên 01769; lớp E403 được xác nhận từ kết quả chấm điểm trên hệ thống web competition.

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Command Line Interface | `cli.py` | Tham số dòng lệnh, config | Kết quả chạy hoặc JSON | Hoàn thành |
| Schema validation | `schemas/input.schema.json`, `schemas/output.schema.json` | Input/output file | Validated JSON | Hoàn thành |
| Local grader | `local_grader.py` | Output files, trace logs, CSV | Component score, total score | Hoàn thành |
| Money & datetime helpers | `money.py` | Currency string, timestamp | Decimal, datetime | Hoàn thành |
| ZIP packaging | `cli.py` packaging logic | Output folder, logging folder | deliverable.zip | Hoàn thành |
| Configuration management | `config.py`, `env setup` | Environment variables | Configuration object | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
|---|---|---|
| Hỗ trợ integration | Coordinator + Domain Agents | Đảm bảo giao tiếp qua typed contracts |
| Audit data pipeline | Input validation, CSV processing | Xác nhận toàn bộ 50 case được xử lý đúng |
| Documentation & runbook | README, RUNBOOK, architecture doc | Hướng dẫn setup, chạy, và kiểm thử |
| Test infrastructure | Pytest configuration, test utilities | Cơ sở hạ tầng kiểm thử cho toàn bộ hệ thống |

## 3. Kết quả theo vai trò

| Nhiệm vụ | Artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| CLI run command | `python -m dispute_agents.cli run` | 50/50 case xử lý thành công | Kiểm tra output folder |
| CLI grade command | `python -m dispute_agents.cli grade` | Điểm 100.0, 0 hard gate | Chạy lệnh grade |
| Schema validation | `schemas/input.schema.json`, `output.schema.json` | Tất cả 50 output match schema | JSON schema validator |
| Money conversion | `money.py` functions | Decimal precision, datetime parsing | Unit tests pass |
| ZIP packaging | `deliverable.zip` | File chứa output, logging, metadata | Unzip và kiểm tra cấu trúc |
| Configuration | `.env`, `config.py` | Model name, API key management | Load config, verify values |

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Một hệ thống multi-agent hoàn chỉnh không chỉ bao gồm logic xử lý mà còn cần:
1. Interface dòng lệnh dễ sử dụng để chạy end-to-end
2. Validation schema chặt chẽ đảm bảo input/output tương thích
3. Bộ grader local để kiểm thử nhanh mà không phải truyền qua hệ thống web
4. Quản lý tiền tệ chính xác với `Decimal` thay vì float
5. Đóng gói kết quả sạch sẽ theo format yêu cầu

### Cách triển khai

- **CLI Module** (`cli.py`): Xây dựng command group với `run`, `grade`, `validate`, `package` subcommands. Mỗi command gọi tới module tương ứng và xử lý error gracefully.
- **Schema Validation** (`schemas/`): Sử dụng JSON Schema để định nghĩa structure của input (case_id, claimed_order_id, policy_version) và output (resolution, refund, action, evidence). Validator kiểm tra mỗi file trước khi đọc hoặc ghi.
- **Money Helpers** (`money.py`): Hàm `parse_currency()` chuyển string "12.50" thành Decimal("12.50") để tránh sai số dấu phẩy động; `csv_timestamp()` xử lý chuỗi rỗng hoặc `NaN` từ CSV.
- **Local Grader** (`local_grader.py`): Đọc từng output file, parse resolution type, so sánh với expected từ oracle (CSV + logic), tính điểm từng component (resolution accuracy, refund accuracy, action correctness, evidence validity, root cause correctness, trace completeness).
- **ZIP Packaging**: Sau khi run thành công, gom output/ và logging/ vào deliverable.zip theo format yêu cầu.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | JSON file chứa case_id, claimed_order_id, customer request |
| Output schema | JSON với 7 field: resolution, responsible_party, refund, action, evidence, trace_count, metadata |
| CLI entry point | `python -m dispute_agents.cli run \| grade \| validate` |
| Error handling | Schema validation fail, file not found, currency parse error, datetime parse error |
| Deliverable format | ZIP chứa /output (50 file), /logging (trace.jsonl, metadata.json) |

### Cách xác minh

```powershell
$env:PYTHONPATH = "src"
python -m dispute_agents.cli run          # Chạy 50 case
python -m dispute_agents.cli grade        # Chấm điểm local
python -m dispute_agents.cli validate     # Kiểm tra schema
python -m dispute_agents.cli package      # Đóng gói ZIP
```

- Kết quả mong đợi: Run pass hết 50 case, grade = 100.0, validate pass, package tạo ZIP thành công.
- Kết quả thực tế: Toàn bộ pass, ZIP tạo thành công với cấu trúc đúng.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh**: Cần quản lý tiền tệ chính xác và đảm bảo output luôn valid schema trước khi nộp.
- **Phương án cân nhắc**:
  1. Dùng float cho tiền tệ, dùng string validation đơn giản.
  2. Dùng Decimal cho tiền tệ, JSON Schema cho output validation.
- **Phương án chọn**: Phương án 2.
- **Lý do**: `Decimal` tránh lỗi làm tròn (0.1 + 0.2 = 0.30000000000000004 với float), JSON Schema đảm bảo mọi output đúng contract trước ghi file.
- **Bằng chứng**: Hai lần chạy có checksum cùng, local grader exact 100.0 trên sáu component.

## 6. Một lỗi hoặc blocker đã xử lý

**Vấn đề**: Một số CSV file có giá trị tiền tệ với dấu phẩy thay vì dấu chấm (vd "12,50" thay vì "12.50"), hoặc có ký tự BRL (vd "R$12.50"). Parse trực tiếp gây ValueError.

**Giải quyết**: Viết hàm `parse_currency()` trong `money.py` để normalize: loại bỏ "R$", thay "," thành ".", sau đó parse thành Decimal. Thêm unit test kiểm tra tất cả format có thể gặp từ CSV.

## 7. Hiểu biết end-to-end

1. User chạy `python -m dispute_agents.cli run`.
2. CLI load config từ `.env` (model name, API key nếu có).
3. Cho mỗi input file, CLI gọi Coordinator.
4. Coordinator gọi OrderSeller, Payment, Delivery agents; các agent return typed findings.
5. Coordinator gọi Policy để tạo resolution, sau đó gọi Verifier để verify.
6. Verifier dùng access control đọc lại dữ liệu từ CSV, so exact với resolution.
7. Nếu verify pass, output được ghi ra file JSON (được validate schema).
8. Sau 50 case, user chạy `python -m dispute_agents.cli grade` để kiểm local score.
9. User chạy `python -m dispute_agents.cli package` để tạo deliverable.zip.
10. File ZIP được submit lên web grader; web grader kiểm tra output file, tính điểm theo oracle khác.

## 8. Rủi ro và giới hạn

- JSON Schema validator có hỗ trợ công khai, nhưng web grader có thể có extra validation rule không công bố.
- Local grader reverse-engineer từ README + CSV oracle, không thể xác minh chính xác hard gate logic của web grader.
- CLI không hỗ trợ resume checkpoint; nếu fail giữa chừng case #30, phải chạy lại từ case #1.
- Money helpers chỉ hỗ trợ Decimal + quantize(0.01); nếu data có multiple currency, cần refactor.
- Schema validation chỉ check structure, không check business logic (vd: refund=0 khi nên > 0).
- Không có rate limiting; nếu integrate LLM audit thực tế, có thể hit API quota mà không retry.
- Packaging strict 50 file; nếu output folder có file ngoài pattern, ZIP sẽ skip và ghi warning.

## 9. Tự đánh giá

- [x] CLI run command hoạt động, 50/50 case output thành công.
- [x] Schema validation pass cho input và output.
- [x] Local grader đạt 100.0, 0 hard gate, sáu component 100.
- [x] Money parsing dùng Decimal + quantize(0.01), zero precision loss.
- [x] ZIP packaging tạo deliverable.zip với cấu trúc đúng output/ và logging/.
- [x] Configuration management load từ `.env` và `config.py`.
- [x] CLI help text chi tiết, RUNBOOK hướng dẫn setup.
- [x] Web grader E403/01769 xác nhận score trên hệ thống.
- [ ] Organizer xác nhận exact hard gate rules và component weights.
- [ ] Repository owner cung cấp API key thật nếu bắt buộc LLM audit.

Người báo cáo: Trần Tuấn Trung
Ngày: 2026-08-05

---


