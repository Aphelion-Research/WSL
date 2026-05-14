from __future__ import annotations

import re
from pathlib import Path

from ragd_chunker.chunker import ASTChunk, content_hash, module_name

_FUNC = re.compile(r"^\s*(?:template\s*<[^>]+>\s*)?(?:[\w:<>~*&]+\s+)+(?P<name>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)?)\s*\([^;]*\)\s*(?:const\s*)?\{")
_CLASS = re.compile(r"^\s*(class|struct)\s+(?P<name>[A-Za-z_]\w*)")
_INCLUDE = re.compile(r"^\s*#include\s+[<\"]([^>\"]+)[>\"]")
_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def _find_block_end(lines: list[str], start_index: int) -> int:
    depth = 0
    seen = False
    for index in range(start_index, len(lines)):
        depth += lines[index].count("{")
        if "{" in lines[index]:
            seen = True
        depth -= lines[index].count("}")
        if seen and depth <= 0:
            return index + 1
    return start_index + 1


def chunk_cpp(filepath: str, content: str) -> list[ASTChunk]:
    lines = content.splitlines()
    imports = sorted(dict.fromkeys(match.group(1) for line in lines for match in [_INCLUDE.match(line)] if match))
    module = module_name(filepath)
    chunks: list[ASTChunk] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        class_match = _CLASS.match(line)
        func_match = _FUNC.match(line)
        if class_match:
            name = class_match.group("name")
            end = _find_block_end(lines, index)
            chunk_content = "\n".join(lines[index:end])
            chunks.append(ASTChunk(
                filepath=filepath,
                content=chunk_content,
                lang="cpp",
                chunk_type=class_match.group(1),
                symbol_name=name,
                qualified_name=f"{module}.{name}" if module else name,
                parent_symbol="",
                line_start=index + 1,
                line_end=end,
                docstring="",
                imports=imports,
                calls=sorted(set(_CALL.findall(chunk_content))),
                is_public=not name.startswith("_"),
                content_hash=content_hash(chunk_content),
            ))
            index = end
            continue
        if func_match:
            name = func_match.group("name")
            end = _find_block_end(lines, index)
            chunk_content = "\n".join(lines[index:end])
            parent = name.split("::", 1)[0] if "::" in name else ""
            chunks.append(ASTChunk(
                filepath=filepath,
                content=chunk_content,
                lang="cpp",
                chunk_type="method" if parent else "function",
                symbol_name=name.replace("::", "."),
                qualified_name=f"{module}.{name.replace('::', '.')}" if module else name.replace("::", "."),
                parent_symbol=parent,
                line_start=index + 1,
                line_end=end,
                docstring="",
                imports=imports,
                calls=sorted(set(_CALL.findall(chunk_content)) - {name.rsplit("::", 1)[-1]}),
                is_public=not name.startswith("_"),
                content_hash=content_hash(chunk_content),
            ))
            index = end
            continue
        index += 1
    if not chunks:
        from ragd_chunker.chunker import _module_chunk
        return _module_chunk(filepath, content, "cpp")
    return chunks
