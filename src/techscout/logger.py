"""Logging centralizado do TechScout AI.

Este módulo é importado por todos os demais e por isso nunca deve levantar
exceção na importação: se o diretório de logs não for gravável (container com
filesystem somente-leitura, CI, sandbox), o handler de arquivo é omitido e o
logger segue funcionando apenas com o console.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from techscout.settings import settings

_MAX_LOG_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5


def _console_handler(formatter: logging.Formatter) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    return handler


def _file_handler(formatter: logging.Formatter) -> logging.Handler | None:
    """Handler de arquivo com rotação, ou None se o destino não for gravável."""
    try:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=_MAX_LOG_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        # Sem log em arquivo é degradação aceitável; sem console não seria.
        return None
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    return handler


def setup_logger(name: str = "techscout") -> logging.Logger:
    """Configura o logger com saída para console e, quando possível, arquivo."""
    logger = logging.getLogger(name)

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.addHandler(_console_handler(formatter))

    file_handler = _file_handler(formatter)
    if file_handler is not None:
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()
