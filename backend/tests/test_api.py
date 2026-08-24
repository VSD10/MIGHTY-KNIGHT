import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health_and_config():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    cfg_resp = client.get("/api/config")
    assert cfg_resp.status_code == 200
    assert "student_levels" in cfg_resp.json()

def test_api_schedule_workflow():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    assert os.path.exists(sample_path)

    # 1. Upload Excel file first
    with open(sample_path, "rb") as f:
        upload_resp = client.post("/api/upload", files={"file": ("mighty_knight_template.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert upload_resp.status_code == 200
    assert upload_resp.json()["total_students_parsed"] > 0

    # 2. Trigger scheduling run
    req = {
        "start_date": "2026-08-24",
        "end_date": "2026-08-30"
    }
    resp = client.post("/api/schedule/run", json=req)
    assert resp.status_code == 200
    data = resp.json()
    schedule_id = data["schedule_id"]
    assert schedule_id is not None

    # 3. Fetch Output 1
    o1 = client.get(f"/api/schedule/{schedule_id}/output1")
    assert o1.status_code == 200
    assert "whatsapp_plain_text" in o1.json()

    # 4. Fetch Output 2
    o2 = client.get(f"/api/schedule/{schedule_id}/output2")
    assert o2.status_code == 200
    assert "detailed_classes" in o2.json()

    # 5. Fetch Output 3
    o3 = client.get(f"/api/schedule/{schedule_id}/output3")
    assert o3.status_code == 200
    assert "attention_records" in o3.json()

    # 6. Status toggle
    st_resp = client.post(f"/api/schedule/{schedule_id}/status", json={"status": "Finalized"})
    assert st_resp.status_code == 200
    assert st_resp.json()["status"] == "Finalized"
