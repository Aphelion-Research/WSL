from __future__ import annotations

from pathlib import Path

from ragd_chunker.chunker import chunk_file


def test_python_chunker_symbols_and_boundaries():
    path = Path(__file__).parent / "fixtures" / "sample.py"
    chunks = chunk_file(str(path), path.read_text(), "python")
    by_name = {chunk.symbol_name: chunk for chunk in chunks}
    assert {"Greeter", "Greeter.greet", "helper"} <= set(by_name)
    assert by_name["Greeter"].chunk_type == "class"
    assert by_name["Greeter.greet"].chunk_type == "method"
    assert by_name["Greeter.greet"].parent_symbol == "Greeter"
    assert by_name["Greeter.greet"].docstring == "Return a greeting."
    assert "pathlib" in {item.lower().strip(".") for item in by_name["helper"].imports}
    assert by_name["helper"].line_start < by_name["helper"].line_end
