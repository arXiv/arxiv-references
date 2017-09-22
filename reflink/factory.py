"""Application factory for reflink service components."""

from flask import Flask
from celery import Celery

import logging


def create_web_app() -> Flask:
    """Initialize an instance of the web application."""
    from reflink.web import rest
    from reflink.services.data_store import referencesStore
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('reflink', static_folder='web/static',
                template_folder='web/templates')
    app.config.from_pyfile('config.py')
    referencesStore.init_app(app)
    app.register_blueprint(rest.blueprint)
    return app


def create_process_app() -> Celery:
    """Initialize an instance of the processing application."""
    from reflink.celery import app
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)
    return app
