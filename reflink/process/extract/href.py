"""
HREF extraction module.

Provides a wrapper for `PDFx <https://www.metachris.com/pdfx/>`_, which
extracts links from PDFs.
"""

import pdfx
import logging

log_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
logging.basicConfig(format=log_format)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _transform(metadatum: pdfx.backends.Reference) -> dict:
    """
    Transform pdfx reference metadata into a valid extraction.

    Parameters
    ----------
    :class:`pdfx.backends.Reference`

    Returns
    -------
    dict
    """
    raw = metadatum['href']
    if not raw.startswith('http'):
        metadatum['href'] = 'http://%s' % raw
    metadatum.update({'reftype': 'href', 'raw': raw})
    return metadatum


def extract_references(pdf_path: str) -> list:
    """
    Extract HREFs from an arXiv PDF.

    Parameters
    ----------
    pdf_path : str

    Returns
    -------
    list
    """
    try:
        pdf = pdfx.PDFx(pdf_path)
        raw = set([ref.ref for ref in pdf.get_references()])
        return list(map(_transform, [{'href': ref} for ref in raw]))
    except Exception as e:
        msg = 'Failed to extract hyperlinks from %s' % pdf_path
        raise RuntimeError(msg) from e
