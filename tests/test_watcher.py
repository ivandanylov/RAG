from pathlib import Path

import local_dev_rag.watcher as watcher


class DummyProject:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.project_id = "demo"
        self.docs = type("Docs", (), {"include": [], "exclude": []})()
        self.code = type("Code", (), {"include": [], "exclude": []})()


def test_main_handles_keyboard_interrupt(monkeypatch, capsys):
    project = DummyProject(Path("/tmp/project"))

    monkeypatch.setattr(watcher, "load_projects", lambda: [project])
    monkeypatch.setattr(watcher, "watch", lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt))

    watcher.main()

    captured = capsys.readouterr()
    assert "Stopping watcher" in captured.out
