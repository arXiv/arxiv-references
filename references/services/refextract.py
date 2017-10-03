"""Service integration for RefExtract."""

import requests
import os
from references import logging
# See http://flask.pocoo.org/docs/0.12/extensiondev/
from flask import _app_ctx_stack as stack
from urllib.parse import urljoin
logger = logging.getLogger(__name__)


class RefExtractSession(object):
    """Provides an interface to RefExtract."""

    def __init__(self, endpoint: str) -> None:
        """Set the endpoint for Refextract service."""
        self.endpoint = endpoint
        response = requests.get(urljoin(self.endpoint, '/refextract/status'))
        if not response.ok:
            raise IOError('Refextract endpoint not available: %s' %
                          response.content)

    def extract_references(self, filename):
        """
        Extract references from the PDF at ``filename``.

        Parameters
        ----------
        filename : str

        Returns
        -------
        dict
            Raw output from RefExtract.
        """
        response = requests.post(urljoin(self.endpoint, '/refextract/extract'),
                                 files={'file': open(filename, 'rb')},
                                 timeout=300)
        if not response.ok:
            raise IOError('%s: Refextract extraction failed: %s' %
                          (filename, response.content))
        return response.json()


class RefExtract(object):
    """RefExtract integration from references worker application."""

    def __init__(self, app=None):
        """Set and configure application, if provided."""
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        """Configure an application instance."""
        pass

    def get_session(self) -> None:
        """Create a new :class:`.RefExtractSession`."""
        try:
            endpoint = self.app.config['REFEXTRACT_ENDPOINT']
        except (RuntimeError, AttributeError) as e:   # No application context.
            endpoint = os.environ.get('REFEXTRACT_ENDPOINT')
        return RefExtractSession(endpoint)

    @property
    def session(self):
        """Get or create a :class:`.RefExtractSession` for this context."""
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'refextract'):
                ctx.refextract = self.get_session()
            return ctx.refextract
        return self.get_session()     # No application context.


refExtract = RefExtract()