from unittest.mock import MagicMock

import main


def test_start_backend_limits_reload_to_app(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(main.uvicorn, "run", run)

    main.start_backend("0.0.0.0", 8000, reload=True, log_level="info")

    run.assert_called_once_with(
        "app.api.router:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[main.BACKEND_DIR],
        reload_includes=["*.py"],
        log_level="info",
    )
