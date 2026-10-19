import json
import sys

import pytest

from scripts import probar_flujo_real as runner


def test_runner_sin_confirmacion_aborta_antes_de_cualquier_http(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["probar_flujo_real.py", "--output-dir", str(tmp_path)])
    monkeypatch.setattr(
        runner, "request_json",
        lambda *args, **kwargs: pytest.fail("No debe hacer HTTP sin --allow-notifications"),
    )

    with pytest.raises(SystemExit) as error:
        runner.main()

    assert error.value.code == 2


def test_runner_con_confirmacion_continua_sin_http_real(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys, "argv",
        ["probar_flujo_real.py", "--allow-notifications", "--output-dir", str(tmp_path)],
    )
    http_calls = []

    def fake_request(url, *args, **kwargs):
        http_calls.append(url)
        return {"http_status": 200, "body": {"status": "ok"}}

    monkeypatch.setattr(runner, "request_json", fake_request)
    monkeypatch.setattr(
        runner, "run_case",
        lambda case, webhook, api: {
            "case": case["case"], "webhook": {"http_status": case["status"]},
            "elapsed_seconds": 0, "checks": {"stubbed": True}, "passed": True,
        },
    )

    assert runner.main() == 0
    assert http_calls == [runner.DEFAULT_API + "/health"]
    artifacts = list(tmp_path.glob("*.json"))
    assert len(artifacts) == 1
    artifact = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert artifact["email_sending"] == "gestionado_por_workflow; no_verificado_por_runner"
    assert artifact["passed"] == len(runner.CASES)
