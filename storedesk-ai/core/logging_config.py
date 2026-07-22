import logging

from config.settings import settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure application logging once.

    Uvicorn only configures its own loggers, so without this our module
    loggers (provider manager, gateway, agents) would emit nothing and real
    failures would be invisible. We attach a stream handler to the root logger
    and align uvicorn's loggers with the same level.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    for uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(uvicorn_logger).setLevel(level)

    _CONFIGURED = True
