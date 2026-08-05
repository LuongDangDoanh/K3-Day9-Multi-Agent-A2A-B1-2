# Runbook

## 1. Cấu hình

Python 3.10+ là đủ; workflow production không có dependency bên thứ ba.

```powershell
python -m pip install -e .
```

File `.env` chỉ chứa một biến secret:

```dotenv
OPENAI_API_KEY=...
```

Tên model nằm cố định trong `src/dispute_agents/config.py`, không nằm trong `.env`.

## 2. Chạy end-to-end

Chế độ mặc định dùng dữ liệu CSV và policy deterministic:

```powershell
$env:PYTHONPATH = "src"
python -m dispute_agents.cli run
```

Nếu đã có API key và muốn chạy thêm audit Structured Outputs bằng `gpt-4o-mini`:

```powershell
python -m dispute_agents.cli run --llm-audit
```

LLM audit không được phép sửa entity, evidence, số tiền hay policy decision. Verifier CSV vẫn là gate cuối cùng.

## 3. Kiểm thử và chấm local

```powershell
python -m pytest
python -m dispute_agents.cli grade
```

Kỳ vọng: 50 output, 0 hard gate, 100.0 cho assessment/entities/root/evidence/financial/actions.

Local grader tái tính oracle từ README và CSV. Frontend công khai không chứa implementation scorer phía server, nên công cụ này không được mô tả là bản sao byte-for-byte của grader riêng tư.

## 4. Đóng gói

```powershell
python -m dispute_agents.cli package --destination submission.zip
```

ZIP tạo ra có đúng 50 file từ `output/EC_001.json` đến `output/EC_050.json`. Không có `.env`, source, trace, metadata hoặc file lạ.
