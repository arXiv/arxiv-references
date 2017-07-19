"""Unit tests for the :mod:`reflink.notification.consumer` module."""
import unittest
from unittest import mock
import json
from amazon_kclpy import kcl

from reflink.notification import consumer


class TestRecordProcessor(unittest.TestCase):
    """Test the :meth:`.consumer.RecordProcessor.process_records` method."""

    @mock.patch('reflink.notification.process.process_document')
    def test_process_document_called_for_each_record(self, process_document):
        """
        Ensure :func:`reflink.process.orchestrate.process_document` is called.

        The document id from each record should be passed to the
        :func:`reflink.process.orchestrate.process_document` function.
        """
        process_document.return_value = None

        records = mock.MagicMock()
        checkpointer = mock.MagicMock()
        checkpointer.checkpoint = mock.MagicMock(return_value=None)

        _records = []
        for i in range(5):
            record = mock.MagicMock()
            data = {'document_id': 'bar %i' % i}
            record.binary_data = json.dumps(data).encode('utf-8')
            record.sequence_number = i
            record.sub_sequence_number = 0
            record.partition_key = 'thebestpartition111'
            record.checkpointer = checkpointer
            _records.append(record)
            if i == 4:
                last = data['document_id']
        records.records = _records

        processor = consumer.RecordProcessor()
        processor.initialize(None)
        processor.process_records(records)

        self.assertEqual(process_document.call_count, 5)
        self.assertEqual(process_document.call_args[0][0], last)

    def test_bad_data_ends_execution(self):
        """Test the case that the notification data is malformed."""
        pass


class TestRecordProcessorCheckpoint(unittest.TestCase):
    """Test the functionality of the checkpoint mechanism."""

    def test_checkpoint_handles_ShutdownException(self):
        """
        Test the case that a ShutdownException is raised during processing.

        When a CheckpointError (ShutdownException) is raised, should not
        attempt to retry checkpointing.
        """
        checkpointer = mock.MagicMock()

        def _side_effect(seq, subseq):
            raise kcl.CheckpointError('ShutdownException')
        checkpointer.checkpoint = mock.MagicMock(side_effect=_side_effect)

        processor = consumer.RecordProcessor()
        processor.initialize(None)
        processor.checkpoint(checkpointer, 1, 2)

        self.assertEqual(checkpointer.checkpoint.call_count, 1)

    def test_checkpoint_handles_InvalidStateException(self):
        """
        Test the case that an InvalidStateException is raised.

        When a CheckpointError (InvalidStateException) is raised, should retry
        several times.
        """
        checkpointer = mock.MagicMock()

        def _side_effect(seq, subseq):
            raise kcl.CheckpointError('InvalidStateException')
        checkpointer.checkpoint = mock.MagicMock(side_effect=_side_effect)

        processor = consumer.RecordProcessor()
        processor.initialize(None)
        retries = 5
        processor._SLEEP_SECONDS = 0.1    # So that we don't wait all day.
        processor._CHECKPOINT_RETRIES = retries
        processor.checkpoint(checkpointer, 1, 2)

        self.assertEqual(checkpointer.checkpoint.call_count, retries)

    def test_checkpoint_handles_ThrottlingException(self):
        """
        Test the case that a ThrottlingException is raised.

        When a CheckpointError (ThrottlingException) is raised, should retry
        several times.
        """
        checkpointer = mock.MagicMock()

        def _side_effect(seq, subseq):
            raise kcl.CheckpointError('ThrottlingException')
        checkpointer.checkpoint = mock.MagicMock(side_effect=_side_effect)

        processor = consumer.RecordProcessor()
        processor.initialize(None)
        retries = 5
        processor._SLEEP_SECONDS = 0.1    # So that we don't wait all day.
        processor._CHECKPOINT_RETRIES = retries
        processor.checkpoint(checkpointer, 1, 2)

        self.assertEqual(checkpointer.checkpoint.call_count, retries)


class TestRecordProcessorShutdown(unittest.TestCase):
    """Test the handling of Shutdown signals."""

    def test_shutdown_terminate(self):
        """
        Test the case that a TERMINATE signal is passed.

        When :meth:`consumer.RecordProcessor` receives a TERMINATE shutdown
        signal, it should attempt to checkpoint.
        """
        checkpointer = mock.MagicMock()
        checkpointer.checkpoint = mock.MagicMock(return_value=None)
        shutdown = mock.MagicMock()
        shutdown.reason = 'TERMINATE'
        shutdown.checkpointer = checkpointer

        processor = consumer.RecordProcessor()
        processor.shutdown(shutdown)

        self.assertEqual(checkpointer.checkpoint.call_count, 1)

    def test_shutdown_zombie(self):
        """
        Test the case that a ZOMBIE signal is passed.

        When :meth:`consumer.RecordProcessor` receives a ZOMBIE shutdown
        signal, it should not attempt to checkpoint.
        """
        checkpointer = mock.MagicMock()
        checkpointer.checkpoint = mock.MagicMock(return_value=None)
        shutdown = mock.MagicMock()
        shutdown.reason = 'ZOMBIE'
        shutdown.checkpointer = checkpointer

        processor = consumer.RecordProcessor()
        processor.shutdown(shutdown)

        self.assertEqual(checkpointer.checkpoint.call_count, 0)


if __name__ == '__main__':
    unittest.main()
