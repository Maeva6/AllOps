import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging(app):
    """Configure un logging structuré : stdout (Docker) + fichier tournant.

    Flask utilise app.logger pour ses propres messages (requêtes, exceptions
    non interceptées) ; une fois configuré ici, tout passe par le même format.
    """
    level = logging.DEBUG if app.debug else logging.INFO
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    app.logger.handlers.clear()
    app.logger.propagate = False
    app.logger.setLevel(level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    app.logger.addHandler(stream_handler)

    try:
        log_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'), maxBytes=1_000_000, backupCount=3
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        app.logger.addHandler(file_handler)
    except OSError:
        app.logger.warning("Impossible de créer instance/logs — logs fichier désactivés.")

    app.logger.info("Logging configuré (niveau=%s)", logging.getLevelName(level))
