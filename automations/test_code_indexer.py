import pytest
import psycopg2
from psycopg2.extras import execute_values
from unittest.mock import patch, MagicMock

import code_indexer

@patch("code_indexer.execute_values")
@patch("code_indexer.get_embedding")
@patch("code_indexer.psycopg2.connect")
def test_index_project_optimized(mock_connect, mock_get_embedding, mock_execute_values, tmp_path):
    # Setup mock DB
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    # Setup mock embedding
    mock_get_embedding.return_value = [0.1, 0.2, 0.3]

    # Create a dummy project
    p = tmp_path / "dummy_project"
    p.mkdir()
    (p / "test.py").write_text("def foo():\n    pass\n")
    (p / "test2.py").write_text("def bar():\n    pass\n")

    code_indexer.index_project(str(p))

    # Verify execute_values logic
    assert mock_execute_values.called

    # Verify the arguments passed to execute_values
    args, kwargs = mock_execute_values.call_args
    assert args[0] == mock_cur

    # The third argument is the records list
    records = args[2]

    # 2 files, each with 1 chunk (since they are small) = 2 records
    assert len(records) == 2

    # Verify contents of records
    assert records[0][1] == [0.1, 0.2, 0.3] # embedding
    assert records[1][1] == [0.1, 0.2, 0.3] # embedding
