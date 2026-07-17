"""
Smoke test covering the core end-to-end journey:

  health -> register (auto-login) -> me -> create goal -> add task ->
  start/pause/resume/complete a focus block -> analytics reflects it ->
  agent returns a recommendation -> advice-of-the-day.

Runs against the ASGI app with an in-process fake Redis (see conftest).
"""

import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def _register(client):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": "Test User"},
    )
    assert resp.status_code == 201, resp.text
    return email


async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "ok"
    assert body["redis"] == "ok"


async def test_auth_flow(client):
    await _register(client)
    # Cookie is stored on the client; /me should now resolve the session.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert "@example.com" in me.json()["email"]

    # Logout clears the session; /me must then be unauthorized.
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    after = await client.get("/api/v1/auth/me")
    assert after.status_code == 401


async def test_core_journey(client):
    await _register(client)

    # Create a goal.
    goal_resp = await client.post(
        "/api/v1/goals",
        json={
            "title": "Ship the app",
            "category": "career",
            "tags": ["work"],
            "target_date": "2030-01-01",
        },
    )
    assert goal_resp.status_code == 201, goal_resp.text
    goal_id = goal_resp.json()["id"]

    # Add and complete a task.
    task_resp = await client.post(
        f"/api/v1/goals/{goal_id}/tasks", json={"title": "Write the README"}
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]
    done = await client.patch(
        f"/api/v1/goals/{goal_id}/tasks/{task_id}", json={"status": "done"}
    )
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None

    # Focus block: start -> pause -> resume -> complete.
    start = await client.post("/api/v1/focus/start", json={"goal_id": goal_id})
    assert start.status_code == 201
    block_id = start.json()["id"]
    assert (await client.post(f"/api/v1/focus/{block_id}/pause")).status_code == 200
    assert (await client.post(f"/api/v1/focus/{block_id}/resume")).status_code == 200
    complete = await client.post(
        f"/api/v1/focus/{block_id}/complete", json={"notes": "good session"}
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"

    # Analytics reflects the completed task and active goal.
    summary = await client.get("/api/v1/analytics/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["completed_tasks"] >= 1
    assert data["active_goals"] >= 1
    assert len(data["focus_by_day"]) == data["range_days"]

    # Agent recommends the goal we just created.
    rec = await client.get("/api/v1/agent/recommendation")
    assert rec.status_code == 200
    assert rec.json()["suggested_goal_id"] == goal_id
    assert rec.json()["suggested_focus_minutes"] > 0

    # Advice of the day.
    advice = await client.get("/api/v1/advice/today")
    assert advice.status_code == 200
    assert advice.json()["text"]
