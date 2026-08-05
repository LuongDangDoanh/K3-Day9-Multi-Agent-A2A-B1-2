# Báo cáo cá nhân — K3 Day 09 Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Mai Việt Anh |
| MSSV | 2A202601083 |
| Khóa/Lớp | K3 — E403 |
| Vai trò chính | Phát triển các Domain Agents (Order & Seller, Payment, Delivery) và xây dựng bộ kiểm thử (Unit test & Integration test) |
| Ngày hoàn thành | 2026-08-05 |

Thông tin họ tên/MSSV được xác định theo mã học viên 01083; lớp E403 được xác nhận từ kết quả chấm điểm trên hệ thống web competition.

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Order & Seller Agent | `order_seller.py` | Order ID, items, sellers data | OrderSellerFinding | Hoàn thành |
| Payment Agent | `payment.py` | Payments data, expected total | PaymentFinding | Hoàn thành |
| Delivery Agent | `delivery.py` | Orders and item deadlines | DeliveryFinding | Hoàn thành |
| Unit & Integration Tests | `tests/` | Mock data / real CSV data | Test reports (pytest) | Hoàn thành |
| Schema & Money Helper | `money.py` | Raw currency and date strings | Decimal, datetime objects | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
|---|---|---|
| Hỗ trợ Coordinator & Policy | `coordinator.py`, `policy.py` | Tích hợp luồng handoff mượt mà giữa các domain agent và policy |
| Kiểm soát bảo mật | LLM audit & configuration | Đảm bảo an toàn API key và giới hạn kích thước model phù hợp |
| Đóng gói sản phẩm | CLI & ZIP packaging | Tạo command line interface chạy ổn định và nộp bài chính xác |

## 3. Kết quả theo vai trò

| Nhiệm vụ | Artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| Chạy các Domain Agents | `agents/` | 3 agent hoạt động chính xác và deterministic | `python -m pytest` |
| Test coverage & validation | `tests/` | Đạt 100% pass trên 4 file test suite | `python -m pytest` |
| Chấm điểm hệ thống local | Local grader | Đạt 100.0 điểm oracle, không bị lỗi hard gate | `$env:PYTHONPATH = "src"; python -m dispute_agents.cli grade` |
| Kết quả nộp web grader | Điểm web của mã 01083 | Đạt 94.9179 điểm trên hệ thống N7 Competition | Bảng điểm E403 tại thời điểm 2026-08-05T11:53:00 |
| Kiểm thử Access Control | `test_access_and_trace.py` | Verifier và các agent truy cập đúng bảng được phân quyền | `python -m pytest` |

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Để xử lý một customer dispute (khiếu nại của khách hàng) hiệu quả, hệ thống multi-agent cần truy xuất và phân tích chéo dữ liệu từ nhiều bảng (orders, order_items, order_payments, sellers). Các agent chuyên biệt về từng domain phải hoạt động tách biệt để đảm bảo nguyên tắc Least Privilege (không agent nào có toàn quyền truy cập toàn bộ cơ sở dữ liệu), đồng thời kết quả xử lý của các domain agent cần được đóng gói dưới dạng các contract cấu trúc chặt chẽ (OrderSellerFinding, PaymentFinding, DeliveryFinding) trước khi gửi về cho Coordinator.

### Cách triển khai

- **OrderSeller Agent**: Truy xuất đơn hàng và các item liên quan từ CSV, tổng hợp thông tin về mã sản phẩm, mã người bán (seller_id), giá trị hàng (price) và phí vận chuyển (freight_value).
- **Payment Agent**: Tính tổng số tiền khách hàng đã thực trả qua tất cả các đợt thanh toán (installment), đối chiếu với tổng số tiền mong đợi (items + freight) từ OrderSeller Agent với sai số cho phép là 0.10 BRL nhằm phát hiện split payment hợp lệ.
- **Delivery Agent**: Phân tích mốc thời gian giao hàng thực tế của đối tác vận chuyển so với thời hạn ước tính (estimated delivery date) và giới hạn giao hàng của người bán (shipping limit date) để phân định trách nhiệm giao muộn thuộc về seller hay bên logistics.
- Sử dụng kiểu dữ liệu `Decimal` cho tiền tệ và chuyển đổi định dạng datetime chuẩn xác để tránh sai số dấu phẩy động hoặc lỗi múi giờ.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `schemas/input.schema.json` và tệp CSV dữ liệu Olist |
| Output | Các domain findings (`OrderSellerFinding`, `PaymentFinding`, `DeliveryFinding`) |
| Module phụ thuộc | Repository read-only, có cơ chế access control nghiêm ngặt |
| Module sử dụng output | Coordinator, policy engine |
| Điều kiện lỗi | Missing order, schema mismatch, invalid evidence, no policy match, math/action/refund mismatch |

### Cách xác minh

```powershell
$env:PYTHONPATH = "src"
python -m pytest
python -m dispute_agents.cli run
```

- Kết quả mong đợi: Các unit test và integration test đều pass thành công; 50 tệp đầu ra được tạo ra đúng cấu trúc.
- Kết quả thực tế: 50 output được tạo đúng cấu trúc tại thư mục `output/`, các kiểm thử đều PASS 100%.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh**: Cần đảm bảo dữ liệu xử lý giữa các domain agent không bị chồng chéo và tuân thủ chặt chẽ phân quyền truy cập (Access Control) nhằm tránh rò rỉ dữ liệu hoặc các tác vụ tính toán không mong muốn.
- **Phương án cân nhắc**: 
  1. Cho phép các agent tự do đọc toàn bộ các file CSV của hệ thống.
  2. Triển khai một repository trung gian có cơ chế phân quyền (Allowlist) cho từng agent dựa trên tên của agent đó.
- **Phương án chọn**: Phương án 2.
- **Lý do**: Tăng tính bảo mật cho hệ thống, cô lập các lỗi lập trình và đảm bảo tính độc lập của từng module domain. Nếu một agent cố tình truy cập bảng dữ liệu không được phân quyền, hệ thống sẽ ném ra ngoại lệ `AccessViolation` ngay lập tức.
- **Bằng chứng**: File test `tests/test_access_and_trace.py` kiểm tra toàn bộ quyền truy cập và đảm bảo không có vi phạm nào xảy ra.

## 6. Một lỗi hoặc blocker đã xử lý

Trong quá trình phát triển Delivery Agent, việc so sánh các giá trị ngày tháng từ CSV gặp lỗi do một số trường thời gian (`order_delivered_carrier_date` hoặc `order_delivered_customer_date`) bị trống (`NaN` hoặc chuỗi rỗng) đối với các đơn hàng bị hủy hoặc không khả dụng. Ban đầu, việc parse chuỗi datetime trực tiếp gây ra lỗi runtime `ValueError`.

**Giải quyết**: Viết hàm trợ giúp `csv_timestamp` trong `src/dispute_agents/money.py` để xử lý an toàn các giá trị trống, trả về `None` khi không có timestamp và thêm các kiểm tra logic `is not None` trong Delivery Agent trước khi thực hiện các phép so sánh thời gian (`>`).

## 7. Hiểu biết end-to-end

1. Client cung cấp 50 case chứa `claimed_order_id`.
2. Coordinator khởi tạo luồng và gọi `OrderSellerAgent` để trích xuất danh sách sản phẩm, giá cả, và người bán.
3. `PaymentAgent` nhận dữ liệu tổng số tiền dự kiến để đối chiếu và đối chiếu chéo các dòng thanh toán thực tế của khách hàng.
4. `DeliveryAgent` đối chiếu thời gian bàn giao thực tế của carrier với `shipping_limit_date` của từng sản phẩm để xác định lỗi thuộc về ai.
5. Kết quả của ba agent này được Coordinator tổng hợp gửi sang `PolicyAgent` để đưa ra Candidate Resolution.
6. `VerifierAgent` thực hiện kiểm tra chéo độc lập toàn bộ Candidate trước khi cho phép ghi file JSON kết quả cuối cùng.

## 8. Rủi ro và giới hạn

- Hệ thống phụ thuộc nhiều vào định dạng chính xác của các tệp CSV đầu vào Olist. Nếu dữ liệu bị thay đổi cấu trúc hoặc thiếu các trường khóa chính, các domain agent sẽ không thể tìm thấy dữ liệu và trả về lỗi.
- Trách nhiệm giao muộn được xác định theo mốc thời gian lớn hơn (`>`), tuy nhiên trong thực tế có thể có những trường hợp đặc biệt không được ghi nhận trong tập dữ liệu Olist (ví dụ: ngày lễ, thiên tai).

## 9. Tự đánh giá

- [x] Đã hoàn thành 3 domain agents hoạt động độc lập và bảo mật.
- [x] Triển khai thành công bộ unit tests và integration tests đạt tỷ lệ pass 100%.
- [x] Định dạng dữ liệu chính xác (Decimal cho tiền tệ, xử lý datetime an toàn).
- [x] Hệ thống chạy mượt mà E2E, đạt điểm tối đa local oracle.

Người báo cáo: Mai Việt Anh
Ngày: 2026-08-05
