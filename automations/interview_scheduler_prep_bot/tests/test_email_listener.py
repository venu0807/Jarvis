import pytest
from automations.interview_scheduler_prep_bot.email_listener import main_daemon_loop

def test_main_daemon_loop_success(mocker):
    mock_check = mocker.patch("automations.interview_scheduler_prep_bot.email_listener.check_and_process_emails")
    mock_sleep = mocker.patch("time.sleep", side_effect=Exception("Stop loop"))

    with pytest.raises(Exception, match="Stop loop"):
        main_daemon_loop()

    mock_check.assert_called_once()
    mock_sleep.assert_called_once_with(300)

def test_main_daemon_loop_exception_handling(mocker, capsys):
    mock_check = mocker.patch("automations.interview_scheduler_prep_bot.email_listener.check_and_process_emails", side_effect=ValueError("Test Error"))
    mock_sleep = mocker.patch("time.sleep", side_effect=Exception("Stop loop"))

    with pytest.raises(Exception, match="Stop loop"):
        main_daemon_loop()

    mock_check.assert_called_once()
    mock_sleep.assert_called_once_with(300)

    captured = capsys.readouterr()
    assert "Daemon loop error: Test Error" in captured.out
