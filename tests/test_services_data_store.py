"""Tests for the :mod:`reflink.services.data_store` module."""
import unittest
import os
from moto import mock_dynamodb2

from reflink.services import data_store
import logging
for name in ['botocore.endpoint', 'botocore.hooks', 'botocore.auth',
             'botocore.credentials', 'botocore.client',
             'botocore.retryhandler', 'botocore.parsers', 'botocore.waiter',
             'botocore.args']:
    logger = logging.getLogger(name)
    logger.setLevel('ERROR')


schema_path = 'schema/StoredReference.json'
extracted_path = 'schema/ExtractedReference.json'
dynamodb_endpoint = 'http://localhost:4569'
os.environ.setdefault('REFLINK_STORED_SCHEMA', schema_path)
os.environ.setdefault('REFLINK_EXTRACTED_SCHEMA', extracted_path)
# os.environ.setdefault('REFLINK_DYNAMODB_ENDPOINT', dynamodb_endpoint)


valid_data = [
    {
        "raw": "Peirson et al 2015 blah blah",
        "reftype": "journalArticle"
    },
    {
        "raw": "Jones 2012",
        "reftype": "journalArticle"
    },
    {
        "raw": "Majumbdar 1968 etc",
        "reftype": "journalArticle"
    },
    {
        "raw": "The brown fox, 1921",
        "reftype": "journalArticle"
    },
]
document_id = 'arxiv:1234.5678'
version = '0.1'


class StoreReference(unittest.TestCase):
    """The data store should store a reference."""

    @mock_dynamodb2
    def test_invalid_data_raises_valueerror(self):
        """
        Test the case that invalid data are passed to the datastore.

        If the input data does not conform to the JSON schema, we should raise
        a ValueError.
        """
        invalid_data = [{"foo": "bar", "baz": 347}]

        session = data_store.get_session()
        with self.assertRaises(ValueError):
            session.create(document_id, invalid_data, version)

    @mock_dynamodb2
    def test_valid_data_is_stored(self):
        """
        Test the case that valid data are passed to the datastore.

        If the data is valid, it should be inserted into the database.
        """
        session = data_store.get_session()
        extraction, data = session.create(document_id, valid_data, version)

        # Get the data that we just inserted.
        retrieved = session.retrieve_all(document_id, extraction)
        self.assertEqual(len(data), len(retrieved))
        self.assertEqual(len(valid_data), len(retrieved))


class RetrieveReference(unittest.TestCase):
    """Test retrieving data from the datastore."""

    @mock_dynamodb2
    def test_retrieve_by_arxiv_id_and_extraction(self):
        """
        Test retrieving data for a specific document from the datastore.

        After a set of references are saved, we should be able to retrieve
        those references using the arXiv identifier and extraction id.
        """
        session = data_store.get_session()
        extraction, data = session.create(document_id, valid_data, version)

        retrieved = session.retrieve_all(document_id, extraction)
        self.assertEqual(len(data), len(valid_data))

        # Order should be preserved.
        for original, returned, final in zip(valid_data, data, retrieved):
            self.assertEqual(original['raw'], returned['raw'])
            self.assertEqual(original['raw'], final['raw'])

    @mock_dynamodb2
    def test_retrieve_latest_by_arxiv_id(self):
        """
        Test retrieving data for the latest extraction from a document.

        After a set of references are saved, we should be able to retrieve
        the latest references using the arXiv identifier.
        """
        session = data_store.get_session()
        first_extraction, _ = session.create(document_id, valid_data, version)
        new_version = '0.2'
        second_extraction, _ = session.create(document_id, valid_data[::-1],
                                              new_version)

        data = session.retrieve_latest(document_id)
        self.assertEqual(len(data), len(valid_data),
                         "Only one set of references should be retrieved.")

        # Order should be preserved.
        for first, second, final in zip(valid_data, valid_data[::-1], data):
            self.assertNotEqual(first['raw'], final['raw'])
            self.assertEqual(second['raw'], final['raw'])

    @mock_dynamodb2
    def test_retrieve_specific_reference(self):
        """
        Test retrieving data for a specific reference in a document.

        After a set of references are saved, we should be able to retrieve
        a specific reference by its document id and identifier.
        """
        session = data_store.get_session()
        extraction, data = session.create(document_id, valid_data, version)
        print(data)
        identifier = data[0]['identifier']
        retrieved = session.retrieve(document_id, identifier)
        self.assertEqual(data[0]['raw'], retrieved['raw'])

    @mock_dynamodb2
    def test_retrieving_nonexistant_record_returns_none(self):
        """
        Test retrieving a record that does not exist.

        If the record does not exist, attempting to retrieve it should simply
        return ``None``.
        """
        session = data_store.get_session()
        data = session.retrieve_latest('nonsense')
        self.assertEqual(data, None)

    @mock_dynamodb2
    def test_retrieving_nonexistant_reference_returns_none(self):
        """
        Test retrieving a record that does not exist.

        If the record does not exist, attempting to retrieve it should simply
        return ``None``.
        """
        session = data_store.get_session()
        data = session.retrieve('nonsense', 'gibberish')
        self.assertEqual(data, None)


if __name__ == '__main__':
    unittest.main()
