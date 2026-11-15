"""寝室 / 值日 / 公告 / 消息 / 个人 / 反馈 / 帮助用例。"""
import pytest

API = "/api/v1"


@pytest.mark.asyncio
async def test_my_room_and_facilities(client, student):
    headers, _ = student
    data = (await client.get(f"{API}/dorm/my-room", headers=headers)).json()["data"]
    assert data["title"] == "3号楼 412 室"
    assert data["capacity"] == 4 and data["occupied"] == 4
    assert len(data["facilities"]) == 4
    fault = next(f for f in data["facilities"] if f["status"] == "fault")
    assert fault["name"] == "热水器"


@pytest.mark.asyncio
async def test_members_permission_flag(client, student, leader):
    student_headers, _ = student
    leader_headers = leader
    as_member = (await client.get(f"{API}/dorm/members", headers=student_headers)).json()["data"]
    as_leader = (await client.get(f"{API}/dorm/members", headers=leader_headers)).json()["data"]
    assert as_member["can_edit"] is False
    assert as_leader["can_edit"] is True
    assert len(as_member["items"]) == 4
    assert all("*" in (i.get("phone") or "*") for i in as_member["items"])


@pytest.mark.asyncio
async def test_non_member_cannot_view_room(client):
    other = await client.post(f"{API}/auth/login", json={"account": "20223702", "password": "Abc123456"})
    headers = {"Authorization": f"Bearer {other.json()['data']['access_token']}"}
    members = await client.get(f"{API}/dorm/members", params={"room_id": 1}, headers=headers)
    assert members.status_code == 403
    own = await client.get(f"{API}/dorm/members", headers=headers)
    assert own.json()["data"]["room"] == "6号楼 305 室"


@pytest.mark.asyncio
async def test_rules_permissions_and_limits(client, student, leader):
    student_headers, _ = student
    assert (await client.put(f"{API}/dorm/rules", json={"items": ["测试"]}, headers=student_headers)).json()["code"] == 1003
    ok = await client.put(
        f"{API}/dorm/rules",
        json={"items": ["23:00 后熄灯", "值日按周轮换", "访客 22:00 前离开", "公共物品用后归位", "第五条"]},
        headers=leader,
    )
    assert len(ok.json()["data"]["items"]) == 5

    too_many = await client.put(f"{API}/dorm/rules", json={"items": [f"第{i}条" for i in range(9)]}, headers=leader)
    assert too_many.status_code == 422

    # 恢复为 4 条，保持其他用例稳定
    await client.put(
        f"{API}/dorm/rules",
        json={"items": ["23:00 后熄灯", "值日按周轮换", "访客 22:00 前离开", "公共物品用后归位"]},
        headers=leader,
    )


@pytest.mark.asyncio
async def test_assets_borrow_and_return(client, student):
    headers, _ = student
    assets = (await client.get(f"{API}/dorm/assets", headers=headers)).json()["data"]
    borrowed = next(a for a in assets if a["status"] == "borrowed")
    conflict = await client.post(f"{API}/dorm/assets/{borrowed['id']}/borrow", headers=headers)
    assert conflict.json()["code"] == 5004

    free = next(a for a in assets if a["status"] == "available")
    got = await client.post(f"{API}/dorm/assets/{free['id']}/borrow", headers=headers)
    assert any(a["id"] == free["id"] and a["status"] == "borrowed" for a in got.json()["data"])
    back = await client.post(f"{API}/dorm/assets/{free['id']}/return", headers=headers)
    assert any(a["id"] == free["id"] and a["status"] == "available" for a in back.json()["data"])


@pytest.mark.asyncio
async def test_duty_schedule_today(client, student):
    headers, _ = student
    data = (await client.get(f"{API}/duty/schedule", headers=headers)).json()["data"]
    assert len(data["items"]) == 7
    assert data["today"]["is_today"] is True
    assert data["is_empty"] is False
    assert data["areas"] == ["地面", "桌面", "阳台", "卫浴"]


@pytest.mark.asyncio
async def test_duty_generate_requires_leader(client, student, leader):
    student_headers, _ = student
    denied = await client.post(f"{API}/duty/schedule/generate", json={}, headers=student_headers)
    assert denied.json()["code"] == 1003

    generated = await client.post(f"{API}/duty/schedule/generate", json={}, headers=leader)
    assert generated.json()["code"] == 0
    assert len(generated.json()["data"]["items"]) == 7


@pytest.mark.asyncio
async def test_hygiene_records_and_rectify(client, student, leader):
    student_headers, _ = student
    data = (await client.get(f"{API}/hygiene/checks", headers=student_headers)).json()["data"]
    assert data["items"]
    assert 60 <= data["average"] <= 100
    target = next(i for i in data["items"] if i["rectify_status"] == "required")
    assert target["deduction_text"].startswith("阳台堆物")

    denied = await client.post(
        f"{API}/hygiene/checks/{target['id']}/rectify", json={"media_urls": ["/uploads/a.png"]}, headers=student_headers
    )
    assert denied.json()["code"] == 1003

    done = await client.post(
        f"{API}/hygiene/checks/{target['id']}/rectify", json={"media_urls": ["/uploads/a.png"]}, headers=leader
    )
    assert done.json()["data"]["rectify_status"] == "submitted"


@pytest.mark.asyncio
async def test_notices_read_and_receipt(client, student):
    headers, _ = student
    data = (await client.get(f"{API}/notices", headers=headers)).json()["data"]
    assert data["items"][0]["is_pinned"] is True
    pinned = next(i for i in data["items"] if i["require_receipt"])

    detail = await client.get(f"{API}/notices/{pinned['id']}", headers=headers)
    assert detail.json()["data"]["is_read"] is True

    receipt = await client.post(f"{API}/notices/{pinned['id']}/receipt", headers=headers)
    assert receipt.json()["data"]["receipted"] is True

    other = await client.post(f"{API}/notices/{pinned['id']}/receipt", headers=headers)
    assert other.json()["code"] == 0


@pytest.mark.asyncio
async def test_messages_group_and_read(client, student):
    headers, _ = student
    data = (await client.get(f"{API}/messages", headers=headers)).json()["data"]
    assert data["groups"]
    assert data["unread_total"] >= 0

    unread = (await client.get(f"{API}/messages/unread-count", headers=headers)).json()["data"]
    assert unread["total"] == data["unread_total"]

    if data["items"]:
        other = await client.post(f"{API}/auth/login", json={"account": "20223603", "password": "Abc123456"})
        other_headers = {"Authorization": f"Bearer {other.json()['data']['access_token']}"}
        assert (await client.post(f"{API}/messages/{data['items'][0]['id']}/read", headers=other_headers)).status_code == 403


@pytest.mark.asyncio
async def test_message_preferences_persist(client, student):
    headers, _ = student
    saved = await client.put(f"{API}/messages/preferences", json={"sms_types": ["bill"], "wechat_types": ["bill", "notice"]}, headers=headers)
    assert saved.json()["data"]["sms_types"] == ["bill"]
    fetched = await client.get(f"{API}/messages/preferences", headers=headers)
    assert fetched.json()["data"]["wechat_types"] == ["bill", "notice"]


@pytest.mark.asyncio
async def test_profile_readonly_fields(client, student):
    headers, _ = student
    data = (await client.get(f"{API}/profile", headers=headers)).json()["data"]
    assert data["verified"]["readonly"] is True
    assert data["security"]["device_count"] >= 1

    forbidden = await client.put(f"{API}/profile", json={"student_no": "20223602"}, headers=headers)
    assert forbidden.status_code == 403

    updated = await client.put(
        f"{API}/profile", json={"gender": 1, "emergency_name": "林父", "emergency_phone": "13912345521"}, headers=headers
    )
    assert updated.json()["data"]["emergency_name"] == "林父"


@pytest.mark.asyncio
async def test_feedback_create_and_validate(client, student):
    headers, _ = student
    my_orders = (await client.get(f"{API}/repair/orders", params={"status": "done"}, headers=headers)).json()["data"]["items"]
    order_id = my_orders[0]["id"]

    created = await client.post(
        f"{API}/feedbacks",
        json={"type": "quality", "order_id": order_id, "content": "维修质量不错，但希望上门前电话确认。", "media_urls": []},
        headers=headers,
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["fb_no"].startswith("FB")

    short = await client.post(f"{API}/feedbacks", json={"type": "quality", "content": "太短"}, headers=headers)
    assert short.status_code == 422

    other = await client.post(f"{API}/auth/login", json={"account": "20223603", "password": "Abc123456"})
    other_headers = {"Authorization": f"Bearer {other.json()['data']['access_token']}"}
    stolen = await client.post(
        f"{API}/feedbacks",
        json={"type": "quality", "order_id": order_id, "content": "关联他人工单的测试内容，应当被拒绝。"},
        headers=other_headers,
    )
    assert stolen.status_code == 403


@pytest.mark.asyncio
async def test_help_faq_search(client):
    hit = await client.get(f"{API}/help/faqs", params={"q": "跳闸"})
    items = hit.json()["data"]
    assert items and items[0]["is_self_help"] is True
    empty = await client.get(f"{API}/help/faqs", params={"q": "xyz-not-exist"})
    assert empty.json()["data"] == []
    phones = await client.get(f"{API}/help/hotlines")
    assert len(phones.json()["data"]) == 2


@pytest.mark.asyncio
async def test_home_summary_aggregates(client, student):
    headers, _ = student
    data = (await client.get(f"{API}/home/summary", headers=headers)).json()["data"]
    assert "412 室" in data["greeting"]
    assert data["due"]["count"] >= 1
    assert len(data["services"]) == 6
    assert data["notices"]
