from __future__ import annotations

from fastapi.testclient import TestClient

from web_api.app import create_app


def test_health_endpoint_returns_demo_and_full():
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"demo", "full"}
    assert any(item["name"] == "ref_chapter" for item in payload["demo"])


def test_sessions_endpoint_returns_list():
    client = TestClient(create_app())
    response = client.get("/api/sessions")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_demo_run_and_artifacts_endpoint():
    client = TestClient(create_app())
    session_id = "web-api-test"
    response = client.post(
        "/api/runs/demo",
        json={"session_id": session_id, "force_new_session": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["manifest"]["session_id"] == session_id

    artifacts_response = client.get(f"/api/sessions/{session_id}/artifacts")
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert artifacts["manifest"]["session_id"] == session_id
    assert artifacts["topic"]
    assert artifacts["director"]
    assert artifacts["script_text"]
    assert artifacts["voice"]
    assert artifacts["images"]
    assert artifacts["video"]


def test_full_run_mock_mode_preserves_mooc_path():
    client = TestClient(create_app())
    session_id = "web-api-full-mock-test"
    response = client.post(
        "/api/runs/full",
        json={"session_id": session_id, "execution": "mock"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["manifest"]["mode"] == "demo"
    assert payload["data"]["manifest"]["session_id"] == session_id

    artifacts_response = client.get(f"/api/sessions/{session_id}/artifacts")
    assert artifacts_response.status_code == 200
    assert "Run Pipeline requested" in artifacts_response.json()["run_log"]


def test_real_stage_missing_prerequisite_returns_readable_error():
    client = TestClient(create_app())
    response = client.post(
        "/api/runs/stage",
        json={"session_id": "web-api-real-missing", "stage": "voice", "execution": "real"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "Missing script" in payload["message"]


def test_missing_stage_prerequisite_returns_readable_error():
    client = TestClient(create_app())
    response = client.post(
        "/api/runs/stage",
        json={"session_id": "web-api-missing-input", "stage": "voice"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "script_items.json" in payload["message"]


def test_missing_session_returns_404():
    client = TestClient(create_app())
    response = client.get("/api/sessions/not-exist-for-test")

    assert response.status_code == 404
    assert "manifest" in response.json()["detail"]


def test_upload_source_file_returns_saved_path():
    client = TestClient(create_app())
    client.post(
        "/api/runs/full",
        json={"session_id": "upload-source-test", "execution": "mock"},
    )
    response = client.post(
        "/api/uploads/source",
        data={"session_id": "upload-source-test"},
        files={"file": ("lecture.md", b"# hello\n", "text/markdown")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["filename"] == "lecture.md"
    assert "resources" in payload["data"]["path"]

    manifest_response = client.get("/api/sessions/upload-source-test")
    assert manifest_response.status_code == 200
    assert manifest_response.json()["config_snapshot"]["uploaded_source"].endswith("lecture.md")
    assert manifest_response.json()["stages"]["topic"] == "pending"

    artifacts_response = client.get("/api/sessions/upload-source-test/artifacts")
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert artifacts["source_upload"]["filename"] == "lecture.md"
    assert artifacts["topic"] is None


def test_upload_source_accepts_chinese_filename():
    client = TestClient(create_app())
    response = client.post(
        "/api/uploads/source",
        data={"session_id": "upload-chinese-source-test"},
        files={"file": ("无中生有.md", b"# hello\n", "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["filename"] == "无中生有.md"


def test_upload_source_sanitizes_windows_invalid_filename_chars():
    client = TestClient(create_app())
    response = client.post(
        "/api/uploads/source",
        data={"session_id": "upload-sanitized-source-test"},
        files={"file": ("无中生有:证明.md", b"# hello\n", "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["filename"] == "无中生有_证明.md"


def test_real_full_requires_uploaded_source():
    client = TestClient(create_app())
    response = client.post(
        "/api/runs/full",
        json={"session_id": "real-full-without-source-test", "execution": "real"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "source upload" in payload["message"]


def test_import_script_items_then_run_voice_stage():
    client = TestClient(create_app())
    session_id = "stage-input-upload-test"
    response = client.post(
        "/api/uploads/stage-input",
        data={"session_id": session_id, "stage": "agent_speechers"},
        files={"file": ("script_items.json", b'[{"speaker":"A","content":"hello"}]', "application/json")},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    stage_response = client.post(
        "/api/runs/stage",
        json={"session_id": session_id, "stage": "voice"},
    )

    assert stage_response.status_code == 200
    assert stage_response.json()["ok"] is True


def test_smoke_image_config_does_not_generate_image(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    client = TestClient(create_app())
    response = client.post("/api/smoke", json={"target": "image"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "not called" in payload["message"]


def test_smoke_unknown_target_returns_failed_result():
    client = TestClient(create_app())
    response = client.post("/api/smoke", json={"target": "unknown"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "Unknown" in payload["message"]


def test_tts_smoke_uses_reference_audio_params(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b"RIFF"
        text = ""
        headers = {"content-type": "audio/wav"}

        def raise_for_status(self):
            return None

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("GPT_SOVITS_API_URL", "http://127.0.0.1:9880/tts")
    monkeypatch.setattr("requests.get", fake_get)

    client = TestClient(create_app())
    response = client.post("/api/smoke", json={"target": "tts"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert captured["params"]["ref_audio_path"].endswith("mona_wuyu.wav")
    assert captured["params"]["prompt_text"]
    assert captured["params"]["prompt_lang"] == "zh"
    assert captured["params"]["text_split_method"] == "cut0"
