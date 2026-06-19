from __future__ import annotations

import pytest

from app.utils.chunking import (
    ChunkStrategy,
    chunk_text,
    estimate_token_count,
)


class TestFixedChunking:
    def test_fixed_chunks_basic(self):
        text = "A" * 1000
        chunks = chunk_text(text, strategy=ChunkStrategy.FIXED, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 0
        assert all(len(c) <= 100 for c in chunks)

    def test_fixed_chunks_overlap(self):
        text = "ABCDEFGHIJ"
        chunks = chunk_text(text, strategy=ChunkStrategy.FIXED, chunk_size=5, chunk_overlap=2)
        assert chunks == ["ABCDE", "DEFGH", "GHIJ"]

    def test_fixed_chunks_no_overlap(self):
        text = "ABCDEFGHIJ"
        chunks = chunk_text(text, strategy=ChunkStrategy.FIXED, chunk_size=5, chunk_overlap=0)
        assert chunks == ["ABCDE", "FGHIJ"]

    def test_fixed_chunks_empty_text(self):
        chunks = chunk_text("", strategy=ChunkStrategy.FIXED, chunk_size=100)
        assert chunks == []

    def test_fixed_chunks_invalid_overlap(self):
        with pytest.raises(ValueError, match="chunk_overlap must be smaller than chunk_size"):
            chunk_text("test", strategy=ChunkStrategy.FIXED, chunk_size=10, chunk_overlap=10)


class TestRecursiveChunking:
    def test_recursive_chunks_basic(self):
        text = "Para 1.\n\nPara 2.\n\nPara 3."
        chunks = chunk_text(text, strategy=ChunkStrategy.RECURSIVE, chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 0

    def test_recursive_chunks_respects_separators(self):
        text = "A\n\nB\n\nC"
        chunks = chunk_text(text, strategy=ChunkStrategy.RECURSIVE, chunk_size=10, chunk_overlap=0)
        assert all(len(c) <= 10 for c in chunks)

    def test_recursive_chunks_custom_separators(self):
        text = "A|B|C|D|E"
        chunks = chunk_text(
            text,
            strategy=ChunkStrategy.RECURSIVE,
            chunk_size=5,
            chunk_overlap=0,
            separators=["|"],
        )
        assert len(chunks) > 0


class TestSentenceChunking:
    def test_sentence_chunks_basic(self):
        text = "Sentence one. Sentence two. Sentence three."
        chunks = chunk_text(text, strategy=ChunkStrategy.SENTENCE, max_sentences_per_chunk=2, chunk_size=100)
        assert len(chunks) == 2

    def test_sentence_chunks_respects_max_sentences(self):
        text = "A. B. C. D. E."
        chunks = chunk_text(text, strategy=ChunkStrategy.SENTENCE, max_sentences_per_chunk=2, chunk_size=100)
        assert len(chunks) == 3

    def test_sentence_chunks_respects_chunk_size(self):
        text = "This is a very long sentence that exceeds the chunk size limit. Another sentence."
        chunks = chunk_text(text, strategy=ChunkStrategy.SENTENCE, max_sentences_per_chunk=5, chunk_size=20)
        assert all(len(c) <= 20 for c in chunks)

    def test_sentence_chunks_invalid_max(self):
        with pytest.raises(ValueError, match="max_sentences_per_chunk must be > 0"):
            chunk_text("test", strategy=ChunkStrategy.SENTENCE, max_sentences_per_chunk=0)


class TestTokenApproxChunking:
    def test_token_approx_chunks(self):
        text = "A" * 1000
        chunks = chunk_text(
            text,
            strategy=ChunkStrategy.TOKEN_APPROX,
            chunk_size=100,
            chunk_overlap=20,
            estimated_chars_per_token=4,
        )
        assert len(chunks) > 0
        assert all(len(c) <= 400 for c in chunks)


class TestEstimateTokenCount:
    def test_estimate_token_count_basic(self):
        count = estimate_token_count("A" * 100, estimated_chars_per_token=4)
        assert count == 25

    def test_estimate_token_count_zero_chars_per_token(self):
        count = estimate_token_count("A" * 100, estimated_chars_per_token=0)
        assert count == 25

    def test_estimate_token_count_empty(self):
        count = estimate_token_count("")
        assert count == 0