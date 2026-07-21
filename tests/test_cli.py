from prediction_whale_db.cli import main


def test_status_command_prints_bootstrap_message(capsys) -> None:
    exit_code = main(["status"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "prediction-whale-db scaffold is ready" in captured.out
