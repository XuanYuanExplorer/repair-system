"""电子票据 PDF 生成（reportlab + 中文 CID 字体，无外部字体依赖）。"""
from pathlib import Path

from reportlab.lib.pagesizes import A5
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from app.config import settings
from app.models import Bill, Receipt, User

_FONT = "STSong-Light"
_registered = False


def _ensure_font() -> None:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(UnicodeCIDFont(_FONT))
        _registered = True


def build_receipt_pdf(receipt: Receipt, bill: Bill, user: User) -> tuple[str, str]:
    _ensure_font()
    out_dir = Path(settings.upload_dir) / "receipts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{receipt.receipt_no}.pdf"

    width, height = A5
    c = canvas.Canvas(str(path), pagesize=A5)
    c.setFont(_FONT, 18)
    c.drawString(36, height - 60, "学生宿舍服务平台 · 电子票据")
    c.setFont(_FONT, 10)
    c.drawString(36, height - 80, "DORM SERVICE · ELECTRONIC RECEIPT")

    c.line(36, height - 92, width - 36, height - 92)

    rows = [
        ("票据编号", receipt.receipt_no),
        ("账单编号", bill.bill_no),
        ("缴费人", f"{user.name}（{user.student_no or user.worker_no or '-'}）"),
        ("项目", bill.title),
        ("账期", bill.period),
        ("金额", f"¥{bill.amount:.2f}"),
        ("滞纳金", f"¥{bill.late_fee:.2f}"),
        ("开票抬头", receipt.title or "个人"),
        ("缴纳时间", bill.paid_at.strftime("%Y-%m-%d %H:%M") if bill.paid_at else "-"),
    ]
    y = height - 125
    for label, value in rows:
        c.setFont(_FONT, 11)
        c.drawString(36, y, f"{label}")
        c.setFont(_FONT, 11)
        c.drawRightString(width - 36, y, str(value))
        c.line(36, y - 6, width - 36, y - 6)
        y -= 28

    c.setFont(_FONT, 9)
    c.drawString(36, 60, "本票据由学校财务处统一监管，可在缴费记录中重复下载。")
    c.drawString(36, 44, "如对金额有疑问，请携带学生证至宿管中心财务窗口核实。")
    c.showPage()
    c.save()
    return str(path), f"/uploads/receipts/{receipt.receipt_no}.pdf"
