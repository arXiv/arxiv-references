"""Provides health-check controller(s)."""

from references.services.cermine import cermine
from references.services.data_store import referencesStore
from references.services.events import extractionEvents
from references.services.grobid import grobid
from references.services.metrics import metrics
from references.services.refextract import refExtract

from references import logging
logger = logging.getLogger(__name__)


def _getServices() -> list:
    """Yield a list of services to check for connectivity."""
    return [
        ('datastore', referencesStore),
        ('events', extractionEvents),
        ('metrics', metrics),
        ('grobid', grobid),
        ('cermine', cermine),
        ('refextract', refExtract),
    ]


def _healthy_session(service):
    """Evaluate whether we have an healthy session with ``service``."""
    try:
        print(service)
        service.session
    except Exception as e:
        logger.info('Could not initiate session for %s: %s' %
                    (str(service), e))
        return False
    return True


def health_check() -> dict:
    """Retrieve the current health of service integrations."""
    status = {}
    for name, obj in _getServices():
        logger.info('Getting status of %s' % name)
        status[name] = _healthy_session(obj)
    return status