"""账单与支付用例（TC-PAY 核心项）。"""
import uuid
from datetime import date, timedelta

import pytest

API = "/api/v1"


async def _login(client, account, password="Abc123456"):
    r = await client.post(f"{API}/auth/login", json={"account": account, "password": password})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_bill_summary_and_list(client, student):
    headers, _ = student
    summary = await client.get(f"{API}/bills/summary", headers=headers)
    data = summary.json()["data"]
    assert data["unpaid_count"] >= 2
    assert data["paid_count"] >= 18

    bills = await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=headers)
    items = bills.json()["data"]["items"]
    assert all(i["status"] == "unpaid" for i in items)
    assert all(i["payable"] for i in items)
    assert all(i["type"] != "penalty" or not i["mergeable"] for i in items)


@pytest.mark.asyncio
async def test_bill_detail_has_items_and_formula(client, student):
    headers, _ = student
    bills = await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=headers)
    electricity = next(i for i in bills.json()["data"]["items"] if i["type"] == "electricity")
    detail = await client.get(f"{API}/bills/{electricity['id']}", headers=headers)
    data = detail.json()["data"]
    assert data["detail"]["formula"] == "（239 − 160）× 2.00 元/度"
    assert len(data["detail"]["items"]) == 3


@pytest.mark.asyncio
async def test_bill_idor(client, student):
    headers, _ = student
    bills = await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=headers)
    bill_id = bills.json()["data"]["items"][0]["id"]
    other = await _login(client, "20223603")
    assert (await client.get(f"{API}/bills/{bill_id}", headers=other)).status_code == 403


@pytest.mark.asyncio
async def test_generate_merge_pay_and_receipt(client, admin):
    headers = await _login(client, "20223604")
    me = (await client.get(f"{API}/profile", headers=headers)).json()["data"]

    due = str(date.today() + timedelta(days=10))
    for type_, amount, title in (("electricity", "100.00", "测试电费"), ("water", "300.00", "测试水费")):
        r = await client.post(
            f"{API}/admin/bills/generate",
            json={"type": type_, "period": "2099-01", "title": title, "amount": amount, "due_date": due, "student_ids": [me["id"]]},
            headers=admin,
        )
        assert r.json()["data"]["created"] == 1

    bills = (await client.get(f"{API}/bills", params={"status": "unpaid", "year": "2099"}, headers=headers)).json()["data"]["items"]
    assert len(bills) == 2
    ids = [b["id"] for b in bills]

    key = f"pay-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        f"{API}/payment/create", json={"bill_ids": ids, "channel": "wechat"}, headers={**headers, "Idempotency-Key": key}
    )
    assert created.json()["code"] == 0
    payload = created.json()["data"]
    assert payload["amount"] == "400.00"
    txn = payload["txn_no"]

    repeat = await client.post(
        f"{API}/payment/create", json={"bill_ids": ids, "channel": "wechat"}, headers={**headers, "Idempotency-Key": key}
    )
    assert repeat.json()["data"]["txn_no"] == txn

    # 未支付前查询为 processing
    processing = await client.get(f"{API}/payment/transactions/{txn}", headers=headers)
    assert processing.json()["data"]["status"] == "processing"

    await client.post(f"{API}/payment/mock/pay", params={"txn_no": txn, "success": "true"}, headers=headers)
    result = await client.get(f"{API}/payment/transactions/{txn}", headers=headers)
    data = result.json()["data"]
    assert data["status"] == "success" and data["amount"] == "400.00"
    assert {b["id"] for b in data["bills"]} == set(ids)

    paid = await client.get(f"{API}/bills/{ids[0]}", headers=headers)
    assert paid.json()["data"]["status"] == "paid"

    again = await client.post(f"{API}/payment/create", json={"bill_ids": [ids[0]], "channel": "wechat"}, headers=headers)
    assert again.json()["code"] == 4001

    receipt = await client.post(f"{API}/bills/{ids[0]}/receipt", json={"email": "test@example.edu"}, headers=headers)
    assert receipt.json()["code"] == 0
    rid = receipt.json()["data"]["id"]
    pdf = await client.get(f"{API}/receipts/{rid}/file", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")


@pytest.mark.asyncio
async def test_penalty_cannot_merge(client, admin):
    headers = await _login(client, "20223702")
    me = (await client.get(f"{API}/profile", headers=headers)).json()["data"]
    due = str(date.today() + timedelta(days=5))
    for type_, amount, title in (("penalty", "50.00", "测试罚金"), ("water", "80.00", "测试水费")):
        await client.post(
            f"{API}/admin/bills/generate",
            json={"type": type_, "period": "2099-02", "title": title, "amount": amount, "due_date": due, "student_ids": [me["id"]]},
            headers=admin,
        )
    unpaid = (await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=headers)).json()["data"]["items"]
    penalty = next(b for b in unpaid if b["type"] == "penalty")
    other = next(b for b in unpaid if b["type"] != "penalty")
    r = await client.post(f"{API}/payment/create", json={"bill_ids": [penalty["id"], other["id"]], "channel": "wechat"}, headers=headers)
    assert r.status_code == 422 and r.json()["code"] == 4002


@pytest.mark.asyncio
async def test_amount_tampering_ignored(client, student):
    headers, _ = student
    bills = (await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=headers)).json()["data"]["items"]
    bill = bills[0]
    r = await client.post(
        f"{API}/payment/create",
        json={"bill_ids": [bill["id"]], "channel": "wechat", "amount": "0.01"},
        headers=headers,
    )
    assert r.json()["data"]["amount"] == bill["total"]


@pytest.mark.asyncio
async def test_payment_idor(client, student, admin):
    headers, _ = student
    owner = await _login(client, "20223603")
    me = (await client.get(f"{API}/profile", headers=owner)).json()["data"]
    await client.post(
        f"{API}/admin/bills/generate",
        json={
            "type": "water",
            "period": "2099-03",
            "title": "越权测试水费",
            "amount": "12.00",
            "due_date": str(date.today() + timedelta(days=7)),
            "student_ids": [me["id"]],
        },
        headers=admin,
    )
    bill = (await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=owner)).json()["data"]["items"][0]
    created = await client.post(f"{API}/payment/create", json={"bill_ids": [bill["id"]], "channel": "alipay"}, headers=owner)
    txn = created.json()["data"]["txn_no"]

    assert (await client.get(f"{API}/payment/transactions/{txn}", headers=headers)).status_code == 403
    fake = await client.get(f"{API}/payment/transactions/PAY00000000000000", headers=headers)
    assert fake.status_code == 404


@pytest.mark.asyncio
async def test_payment_callback_requires_signature(client, student):
    r = await client.post(f"{API}/payment/callback/wechat", json={"txn_no": "PAY123"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_records_grouped_and_export(client, student):
    headers, _ = student
    records = (await client.get(f"{API}/bills/records", headers=headers)).json()["data"]
    assert records["groups"]
    assert all("label" in g and g["items"] for g in records["groups"])
    csv = await client.get(f"{API}/bills/records/export", headers=headers)
    assert csv.status_code == 200
    assert "attachment" in csv.headers["content-disposition"]
    from urllib.parse import unquote

    assert "对账单" in unquote(csv.headers["content-disposition"])


@pytest.mark.asyncio
async def test_apply_receipt_on_unpaid_rejected(client, student):
    headers, _ = student
    bills = (await client.get(f"{API}/bills", params={"status": "unpaid"}, headers=headers)).json()["data"]["items"]
    r = await client.post(f"{API}/bills/{bills[0]['id']}/receipt", json={"email": "a@b.com"}, headers=headers)
    assert r.json()["code"] != 0
