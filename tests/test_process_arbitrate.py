"""Unit tests for :mod:`reflink.process.merge.arbitrate`."""

import unittest
from reflink.process.merge import arbitrate


class TestArbitrate(unittest.TestCase):
    """Tests for :func:`reflink.process.merge.arbitrate.arbitrate` function."""

    def test_arbitrate(self):
        """Test successful arbitration with valid data."""
        metadata = [
            ('cermine', {'title': 'yep', 'doi': '10.123/123.4566'}),
            ('refextract', {'title': 'asdf', 'doi': 'nonsense',
                            'volume': '12'}),
            ('alt', {'title': 'nope', 'foo': 'bar', 'volume': 'baz'})
        ]
        valid = [
            ('cermine', {'title': 0.9, 'doi': 0.8}),
            ('refextract', {'title': 0.6, 'doi': 0.1, 'volume': 0.8}),
            ('alt', {'title': 0.1, 'foo': 1.0})
        ]
        priors = [
            ('cermine', {'title': 0.8, 'doi': 0.9}),
            ('refextract', {'title': 0.9, 'doi': 0.2, 'volume': 0.2}),
            ('alt', {'title': 0.2, 'foo': 0.9})
        ]

        final, score = arbitrate.arbitrate(metadata, valid, priors)
        self.assertIsInstance(final, dict)
        self.assertEqual(final['title'], 'yep')
        self.assertEqual(final['doi'], '10.123/123.4566')
        self.assertEqual(final['volume'], '12')
        self.assertEqual(final['foo'], 'bar')
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0.5)

    def test_select(self):
        """Test :func:`.arbitrate._select` returns a sensical score."""
        pooled = {
            'title': {
                'meh': 0.7,
                'yes': 1.5,
                'nope': 0.3
            }
        }
        final, score = arbitrate._select(pooled)
        self.assertEqual(final['title'], 'yes')
        self.assertEqual(score, 0.6)

    def test_select_with_ints(self):
        """Test :func:`.arbitrate._select` works with ``int``s."""
        pooled = {
            'title': {
                'meh': 1,
                'yes': 5,
                'nope': 2
            }
        }
        final, score = arbitrate._select(pooled)
        self.assertEqual(final['title'], 'yes')
        self.assertEqual(score, 0.625)

    def test_similarity_with_strings(self):
        """Test :func:`.arbitrate._similarity` returns sensical values."""
        self.assertEqual(arbitrate._similarity('meh', 'meh'), 1.0)
        self.assertEqual(arbitrate._similarity('meh', 'meb'), 2/3)
        self.assertEqual(arbitrate._similarity('foo', 'fuzz'), 1/4)

    def test_pool_can_math(self):
        """Test :func:`.arbitrate._pool` can math."""
        def _prob_valid(extractor, field):
            return 0.55 if extractor in ['cermine', 'refextract'] else 0.95

        metadata = [('cermine', {'title': 'meh'}),
                    ('refextract', {'title': 'meh'}),
                    ('alt', {'title': 'too good to be true'})]
        pooled = arbitrate._pool(dict(metadata), ['title'], _prob_valid)
        self.assertEqual(pooled['title']['meh'], 1.1)
        self.assertEqual(pooled['title']['too good to be true'], 0.95)

    def test_pooling_matters(self):
        """Two med-scoring values can beat a single high-scoring value."""
        metadata = [
            ('cermine', {'title': 'meh'}),
            ('refextract', {'title': 'meh'}),
            ('alt', {'title': 'too good to be true'})
        ]
        valid = [
            ('cermine', {'title': 0.5}),
            ('refextract', {'title': 0.6}),
            ('alt', {'title': 1.0})
        ]
        priors = [
            ('cermine', {'title': 1.0}),
            ('refextract', {'title': 1.0}),
            ('alt', {'title': 1.0})
        ]
        final, score = arbitrate.arbitrate(metadata, valid, priors)
        self.assertEqual(final['title'], 'meh')
        self.assertLess(score - 0.52, 0.01)

    def test_drop_value_if_prior_missing(self):
        """Test that a field-value is ignored if extractor prior is missing."""
        metadata = [
            ('cermine', {'title': 'yep', 'doi': '10.123/123.4566'}),
            ('refextract', {'title': 'asdf', 'doi': 'nonsense',
                            'volume': '12'}),
            ('alt', {'title': 'nope', 'foo': 'bar', 'volume': 'baz'})
        ]
        valid = [
            ('cermine', {'title': 0.9, 'doi': 0.8}),
            ('refextract', {'title': 0.6, 'doi': 0.1, 'volume': 0.8}),
            ('alt', {'title': 0.1, 'foo': 1.0})
        ]
        priors = [
            ('cermine', {'title': 0.8}),
            ('refextract', {'title': 0.9, 'doi': 0.2, 'volume': 0.2}),
            ('alt', {'title': 0.2, 'foo': 0.9})
        ]

        final, score = arbitrate.arbitrate(metadata, valid, priors)
        self.assertEqual(final['doi'], 'nonsense')

    def test_misaligned_input_raises_valueerror(self):
        """Test that misalignment of input is caught."""
        metadata = [('foo', {}), ('bar', {})]
        valid = [('foo', {}), ('baz', {})]
        priors = [('foo', {}), ('bar', {})]
        with self.assertRaises(ValueError):
            arbitrate.arbitrate(metadata, valid, priors)

        metadata = [('foo', {}), ('bar', {})]
        valid = [('foo', {}), ('bar', {})]
        priors = [('foo', {}), ('baz', {})]
        with self.assertRaises(ValueError):
            arbitrate.arbitrate(metadata, valid, priors)

    def test_arbitrate_all(self):
        """Exercise :func:`reflink.process.merge.arbitrate.arbitrate_all`."""
        metadata = [[
            ('cermine', {'title': 'yep', 'doi': '10.123/123.4567'}),
            ('refextract', {'title': 'asdf', 'doi': 'nonsense',
                            'volume': '12'}),
            ('alt', {'title': 'nope', 'foo': 'bar', 'volume': 'baz'})
        ], [
            ('cermine', {'title': 'yep', 'doi': '10.123/123.4566'}),
            ('refextract', {'title': 'asdf', 'doi': 'nonsense',
                            'volume': '12'}),
            ('alt', {'title': 'nope', 'foo': 'bar', 'volume': 'baz'})
        ]]
        valid = [[
            ('cermine', {'title': 0.9, 'doi': 0.8}),
            ('refextract', {'title': 0.6, 'doi': 0.1, 'volume': 0.8}),
            ('alt', {'title': 0.1, 'foo': 1.0})
        ], [
            ('cermine', {'title': 0.9, 'doi': 0.8}),
            ('refextract', {'title': 0.6, 'doi': 0.1, 'volume': 0.8}),
            ('alt', {'title': 0.1, 'foo': 1.0})
        ]]
        priors = [
            ('cermine', {'title': 0.8, 'doi': 0.9}),
            ('refextract', {'title': 0.9, 'doi': 0.2, 'volume': 0.2}),
            ('alt', {'title': 0.2, 'foo': 0.9})
        ]

        final = arbitrate.arbitrate_all(metadata, valid, priors)
        self.assertIsInstance(final, list)
        self.assertEqual(len(final), 2)
        for obj, score in final:
            self.assertGreater(score, 0.0)
            self.assertLess(score, 1.0)
            self.assertIsInstance(obj, dict)
            self.assertEqual(obj['title'], 'yep')
            self.assertEqual(obj['volume'], '12')
            self.assertEqual(obj['foo'], 'bar')
