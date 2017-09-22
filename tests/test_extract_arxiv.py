"""Tests for :mod:`reflink.process.extract.regex_identifiers`."""

import unittest
from reflink.process.extract import regex_identifiers, regex_arxiv
import re


class TestIdentifierIsPresent(unittest.TestCase):
    """Raw reference string contains an arXiv identifier."""

    def test_identifier_has_subject_tag(self):
        """Identifier with subject classification is detected."""
        raw = """B. Groisman, D. Kenigsberg, T. Mor, \u201dQuantumness\u201d versus \u201dClassicality\u201d of Quantum States, Preprint arXiv:quantph/0703103, (2007)"""
        print(re.findall(regex_arxiv.REGEX_ARXIV_FLEXIBLE, raw))

        document = regex_identifiers.extract_identifiers(raw)
        self.assertEqual(document['arxiv_id'], 'quantph/0703103')
