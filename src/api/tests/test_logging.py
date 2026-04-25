import json
from rcars.logging import setup_logging, get_logger


def test_logger_outputs_json(capsys):
    setup_logging(level="INFO", component="api")
    logger = get_logger()
    logger.info("test_event", action="test", detail="hello")
    captured = capsys.readouterr()
    line = json.loads(captured.out.strip())
    assert line["component"] == "api"
    assert line["action"] == "test"
    assert line["detail"] == "hello"
    assert "timestamp" in line


def test_logger_with_job_id(capsys):
    setup_logging(level="INFO", component="worker")
    logger = get_logger().bind(job_id="abc123")
    logger.info("picked_up", action="picked_up")
    captured = capsys.readouterr()
    line = json.loads(captured.out.strip())
    assert line["job_id"] == "abc123"
    assert line["component"] == "worker"
