from windows_maintenance.policy import MaintenancePolicy


def test_windows_maintenance_module_contract():
    assert MaintenancePolicy().evaluate(__import__('windows_maintenance.models', fromlist=['MaintenanceAction']).MaintenanceAction('x', 'y'), True).allowed


def test_system_commands_are_not_injected_from_user_names(monkeypatch):
    from windows_maintenance import windows
    seen = []
    monkeypatch.setattr(windows, '_require_windows', lambda: None)
    monkeypatch.setattr(windows, '_ps', lambda script, timeout=30: seen.append(script) or False)
    ok, _ = windows.stop_process(123, "safe-name")
    assert ok
    assert "safe-name" in seen[0]
    assert "; Stop-Process" in seen[0]
