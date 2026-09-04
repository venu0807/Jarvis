import quick_setup
import subprocess
from unittest.mock import patch

def test_step():
    with patch("subprocess.run") as mock_run:
        quick_setup.step(99, "Test Title", ["echo", "test"])
        mock_run.assert_called_once_with(["echo", "test"], cwd=quick_setup.BASE)
        print("Test passed successfully!")

if __name__ == "__main__":
    test_step()
