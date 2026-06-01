from backend.providers import claude_projects as cp


def test_lists_recent_projects(tmp_path):
    d = tmp_path / "projects"
    (d / "-Users-omri-foo").mkdir(parents=True)
    (d / "-Users-omri-foo" / "x.jsonl").write_text("{}")
    env = cp.provider({"claude": {"projects_dir": str(d)}})
    assert env["status"] == "ok"
    assert env["items"][0]["name"]  # has a friendly name
    assert "last_active" in env["items"][0]


def test_missing_dir_is_setup():
    env = cp.provider({"claude": {"projects_dir": "/no/such/dir"}})
    assert env["status"] == "setup"
