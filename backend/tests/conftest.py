import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def setup_isolated_test_db(tmp_path_factory):
    """
    Isolates pytest database operations to a temporary test database.
    Prevents unit tests from touching or overwriting the application database in backend/data/chess_scheduler.db.
    """
    temp_dir = tmp_path_factory.mktemp("db")
    test_db_path = str(temp_dir / "test_chess_scheduler.db")
    os.environ["CHESS_DB_PATH"] = test_db_path
    yield
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass
