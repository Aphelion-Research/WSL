from __future__ import annotations

import ast

from ragd_chunker.metadata import python_calls, python_docstring, python_imports


def test_python_metadata_extracts_docstring_imports_calls():
    tree = ast.parse('import os\nfrom pathlib import Path\n\ndef f():\n    """Doc."""\n    return Path(os.getcwd())\n')
    func = tree.body[2]
    assert python_docstring(func) == "Doc."
    assert python_imports(tree) == ["os", "pathlib"]
    assert python_calls(func) == ["Path", "getcwd"]
