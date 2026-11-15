"""报修域用例（TC-RPR 核心项 + 并发抢时段）。"""
import asyncio
import uuid
from datetime import date, timedelta

import pytest

API = "/api/v1"


def order_payload(**kwargs):
    payload = {
        "category": "ac",
        "location_type": "in_room",
        "location_desc": "3号楼412室·室内—空调主机",
        "description": "空调启动后不制冷，出常温风，已连续运转 2 小时。",
        "media_urls": [],
        "require_presence": True,
        "contact_phone": "13888888880",
        "client_request_id": f"test-{uuid.uuid4().hex[:10]}",
    }
    payload.update(kwargs)
    return payload


@pytest.mark.asyncio
async def test_slots_shape(client, student):
    headers, _ = student
    r = await client.get(f"{API}/repair/slots", headers=headers)
    items = r.json()["data"]["items"]
    assert len(items) == 3
    assert any(i["full"] for i in items)  # 今日 14-16 已约满
    assert all(i["left"] == max(i["capacity"] - i["booked"], 0) for i in items)


@pytest.mark.asyncio
async def test_create_order_and_idempotency(client, student):
    headers, _ = student
    payload = order_payload(preferred_date=str(date.today() + timedelta(days=1)), preferred_slot="09-11")
    first = await client.post(f"{API}/repair/orders", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    data = first.json()["data"]
    assert data["order_no"].startswith("WX") and data["status"] == "pending"

    second = await client.post(f"{API}/repair/orders", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["data"]["order_no"] == data["order_no"]


@pytest.mark.asyncio
async def test_slot_full_returns_3002(client, student):
    headers, _ = student
    payload = order_payload(preferred_date=str(date.today()), preferred_slot="14-16")
    r = await client.post(f"{API}/repair/orders", json=payload, headers=headers)
    assert r.status_code == 409 and r.json()["code"] == 3002


@pytest.mark.asyncio
async def test_concurrent_slot_booking_never_oversells(client, student):
    headers, _ = student
    day = str(date.today() + timedelta(days=3))
    slots = await client.get(f"{API}/repair/slots", params={"date": day}, headers=headers)
    target = slots.json()["data"]["items"][1]
    left = target["left"]

    async def book():
        return await client.post(
            f"{API}/repair/orders",
            json=order_payload(preferred_date=day, preferred_slot=target["code"]),
            headers=headers,
        )

    results = await asyncio.gather(*[book() for _ in range(left + 3)])
    codes = [r.json()["code"] for r in results]
    assert codes.count(0) == left
    assert codes.count(3002) == 3

    after = await client.get(f"{API}/repair/slots", params={"date": day}, headers=headers)
    slot = [i for i in after.json()["data"]["items"] if i["code"] == target["code"]][0]
    assert slot["booked"] == slot["capacity"]


@pytest.mark.asyncio
async def test_order_detail_and_idor(client, student):
    headers, _ = student
    created = await client.post(
        f"{API}/repair/orders",
        json=order_payload(preferred_date=str(date.today() + timedelta(days=2)), preferred_slot="16-18"),
        headers=headers,
    )
    order_id = created.json()["data"]["id"]

    detail = await client.get(f"{API}/repair/orders/{order_id}", headers=headers)
    data = detail.json()["data"]
    assert data["timeline"][0]["type"] == "submit"
    assert data["progress"]["percent"] == 12
    assert data["can_edit"] and data["can_cancel"]

    other = await client.post(f"{API}/auth/login", json={"account": "20223603", "password": "Abc123456"})
    other_headers = {"Authorization": f"Bearer {other.json()['data']['access_token']}"}
    assert (await client.get(f"{API}/repair/orders/{order_id}", headers=other_headers)).status_code == 403
    assert (await client.get(f"{API}/repair/orders/999999", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_cancel_releases_slot_and_blocks_late_cancel(client, student):
    headers, _ = student
    day = str(date.today() + timedelta(days=4))
    created = await client.post(
        f"{API}/repair/orders", json=order_payload(preferred_date=day, preferred_slot="09-11"), headers=headers
    )
    order_id = created.json()["data"]["id"]

    before = await client.get(f"{API}/repair/slots", params={"date": day}, headers=headers)
    booked_before = [i for i in before.json()["data"]["items"] if i["code"] == "09-11"][0]["booked"]

    cancel = await client.post(f"{API}/repair/orders/{order_id}/cancel", json={"reason": "临时不需要"}, headers=headers)
    assert cancel.json()["data"]["status"] == "cancelled"

    after = await client.get(f"{API}/repair/slots", params={"date": day}, headers=headers)
    booked_after = [i for i in after.json()["data"]["items"] if i["code"] == "09-11"][0]["booked"]
    assert booked_after == booked_before - 1

    again = await client.post(f"{API}/repair/orders/{order_id}/cancel", json={"reason": "重复"}, headers=headers)
    assert again.json()["code"] == 3001


@pytest.mark.asyncio
async def test_urge_cooldown(client, student):
    headers, _ = student
    created = await client.post(f"{API}/repair/orders", json=order_payload(), headers=headers)
    order_id = created.json()["data"]["id"]

    first = await client.post(f"{API}/repair/orders/{order_id}/urge", headers=headers)
    assert first.json()["code"] == 0 and first.json()["data"]["urge_count"] == 1

    second = await client.post(f"{API}/repair/orders/{order_id}/urge", headers=headers)
    assert second.status_code == 429 and second.json()["code"] == 1004


@pytest.mark.asyncio
async def test_full_flow_assign_accept_finish_verify_rate(client, student, admin, worker):
    headers, _ = student
    created = await client.post(f"{API}/repair/orders", json=order_payload(), headers=headers)
    order_id = created.json()["data"]["id"]

    assign = await client.post(
        f"{API}/admin/repair/orders/{order_id}/assign", json={"worker_id": 2}, headers=admin
    )
    assert assign.json()["data"]["status"] == "assigned"

    accept = await client.post(f"{API}/repair/worker/orders/{order_id}/accept", headers=worker)
    assert accept.json()["data"]["status"] == "fixing"

    finish = await client.post(
        f"{API}/admin/repair/orders/{order_id}/finish",
        json={"note": "更换电容并测试正常", "material_fee": 36},
        headers=admin,
    )
    assert finish.json()["data"]["status"] == "verify"

    verify = await client.post(f"{API}/repair/orders/{order_id}/verify", json={"resolved": True}, headers=headers)
    assert verify.json()["data"]["status"] == "done"

    rate = await client.post(
        f"{API}/repair/orders/{order_id}/rate",
        json={"speed": 5, "attitude": 4, "quality": 5, "content": "很专业", "is_anonymous": True},
        headers=headers,
    )
    assert rate.json()["data"]["avg_score"] == 4.7

    dup = await client.post(
        f"{API}/repair/orders/{order_id}/rate",
        json={"speed": 5, "attitude": 4, "quality": 5},
        headers=headers,
    )
    assert dup.json()["code"] == 3007


@pytest.mark.asyncio
async def test_verify_fail_requires_reason(client, student):
    headers, _ = student
    created = await client.post(f"{API}/repair/orders", json=order_payload(), headers=headers)
    order_id = created.json()["data"]["id"]
    r = await client.post(f"{API}/repair/orders/{order_id}/verify", json={"resolved": False}, headers=headers)
    assert r.json()["code"] == 3001


@pytest.mark.asyncio
async def test_archive_and_media_limit(client, student):
    headers, _ = student
    archive = await client.get(f"{API}/repair/archive", headers=headers)
    data = archive.json()["data"]
    assert data["total_count"] >= 20
    assert sum(d["count"] for d in data["distribution"]) == data["total_count"]

    too_many = order_payload(media_urls=[f"/x/{i}.jpg" for i in range(7)])
    r = await client.post(f"{API}/repair/orders", json=too_many, headers=headers)
    assert r.status_code == 422
