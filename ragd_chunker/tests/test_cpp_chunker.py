from __future__ import annotations

from pathlib import Path

from ragd_chunker.chunker import chunk_file


def test_cpp_chunker_extracts_class_and_function():
    path = Path(__file__).parent / "fixtures" / "sample.cpp"
    chunks = chunk_file(str(path), path.read_text(), "cpp")
    by_name = {chunk.symbol_name: chunk for chunk in chunks}
    assert "Greeter" in by_name
    assert "add" in by_name
    assert by_name["Greeter"].chunk_type == "class"
    assert by_name["add"].chunk_type == "function"
    assert "string" in by_name["Greeter"].imports
