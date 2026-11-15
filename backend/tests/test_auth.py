"""认证与安全用例（对应测试文档 TC-AUTH-001 ~ 029 的核心项）。"""
import pytest

API = "/api/v1"


@pytest.mark.asyncio
async def test_login_success_returns_tokens(client):
    r = await client.post(f"{API}/auth/login", json={"account": "20223601", "password": "Abc123456"})
    body = r.json()
    assert r.status_code == 200 and body["code"] == 0
    data = body["data"]
    assert data["access_token"] and data["refresh_token"]
    assert data["expires_in"] == 7200
    assert data["user"]["is_leader"] is False
    assert data["user"]["room"] == "3号楼 412室"


@pytest.mark.asyncio
async def test_login_phone_success(client):
    r = await client.post(f"{API}/auth/login", json={"account": "13888888880", "password": "Abc123456"})
    assert r.json()["code"] == 0


@pytest.mark.asyncio
async def test_login_wrong_password_is_generic(client):
    r = await client.post(f"{API}/auth/login", json={"account": "20223601", "password": "wrong-pass"})
    assert r.status_code == 401
    assert r.json()["code"] == 2005
    assert "账号" in r.json()["message"]


@pytest.mark.asyncio
async def test_login_unknown_account_same_error(client):
    r = await client.post(f"{API}/auth/login", json={"account": "99999999", "password": "Abc123456"})
    assert r.json()["code"] == 2005


@pytest.mark.asyncio
async def test_disabled_account(client):
    r = await client.post(f"{API}/auth/login", json={"account": "20223801", "password": "Abc123456"})
    assert r.json()["code"] == 2007


@pytest.mark.asyncio
async def test_lockout_after_five_failures(client):
    account = "20223701"
    for _ in range(5):
        await client.post(f"{API}/auth/login", json={"account": account, "password": "bad-pass"})
    r = await client.post(f"{API}/auth/login", json={"account": account, "password": "bad-pass"})
    assert r.status_code == 423
    assert r.json()["code"] == 2006
    assert r.json()["data"]["retry_after"] > 0


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client):
    r = await client.get(f"{API}/home/summary")
    assert r.status_code == 401 and r.json()["code"] == 1001


@pytest.mark.asyncio
async def test_tampered_token(client, student):
    headers, _ = student
    token = headers["Authorization"].split()[-1]
    r = await client.get(f"{API}/home/summary", headers={"Authorization": f"Bearer {token[:-4]}abcd"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_detection(client):
    login = await client.post(f"{API}/auth/login", json={"account": "20223603", "password": "Abc123456"})
    refresh = login.json()["data"]["refresh_token"]

    first = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert first.json()["code"] == 0
    new_refresh = first.json()["data"]["refresh_token"]
    assert new_refresh != refresh

    reuse = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert reuse.status_code == 401
    # 复用旧 token 触发全量吊销
    again = await client.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh})
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_logout_blacklists_access(client):
    login = await client.post(f"{API}/auth/login", json={"account": "20223604", "password": "Abc123456"})
    data = login.json()["data"]
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    assert (await client.get(f"{API}/profile", headers=headers)).status_code == 200
    await client.post(f"{API}/auth/logout", json={"refresh_token": data["refresh_token"]}, headers=headers)
    assert (await client.get(f"{API}/profile", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_student_check_preview_and_errors(client):
    ok = await client.get(f"{API}/auth/check-student", params={"student_no": "20223601"})
    data = ok.json()["data"]
    assert data["matched"] and data["bed_no"] == 3 and data["bed_position"] == "lower"
    assert "*" in data["name_masked"]

    missing = await client.get(f"{API}/auth/check-student", params={"student_no": "99999999"})
    assert missing.json()["code"] == 2001

    no_bed = await client.get(f"{API}/auth/check-student", params={"student_no": "20229999"})
    assert no_bed.json()["code"] == 2002


@pytest.mark.asyncio
async def test_register_binds_bed_and_rejects_duplicate(client):
    payload = {"student_no": "20223610", "name": "张可", "phone": "13211112222", "password": "Abc123456"}
    r = await client.post(f"{API}/auth/register", json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["bed_no"] == 1

    dup = await client.post(f"{API}/auth/register", json=payload)
    assert dup.json()["code"] == 2008

    weak = await client.post(
        f"{API}/auth/register", json={**payload, "student_no": "20223601", "password": "123456"}
    )
    assert weak.status_code == 422


@pytest.mark.asyncio
async def test_admin_endpoint_forbidden_for_student(client, student):
    headers, _ = student
    r = await client.get(f"{API}/admin/repair/orders", headers=headers)
    assert r.status_code == 403 and r.json()["code"] == 1003
