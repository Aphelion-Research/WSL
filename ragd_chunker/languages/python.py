from __future__ import annotations

import ast
from pathlib import Path

from ragd_chunker.chunker import ASTChunk, content_hash, module_name
from ragd_chunker.metadata import python_calls, python_docstring, python_imports


def _node_start(node: ast.AST) -> int:
    decorators = getattr(node, "decorator_list", [])
    lines = [getattr(node, "lineno", 1)] + [getattr(decorator, "lineno", getattr(node, "lineno", 1)) for decorator in decorators]
    return min(lines)


def _slice(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1:end])


def _public(name: str) -> bool:
    leaf = name.rsplit(".", 1)[-1]
    return not leaf.startswith("_")


def _class_body_without_methods(lines: list[str], node: ast.ClassDef) -> str:
    excluded: set[int] = set()
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for lineno in range(_node_start(child), getattr(child, "end_lineno", _node_start(child)) + 1):
                excluded.add(lineno)
    body = []
    for lineno in range(_node_start(node), getattr(node, "end_lineno", _node_start(node)) + 1):
        if lineno not in excluded:
            body.append(lines[lineno - 1])
    return "\n".join(body).rstrip()


def chunk_python(filepath: str, content: str) -> list[ASTChunk]:
    lines = content.splitlines()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        from ragd_chunker.chunker import _module_chunk
        return _module_chunk(filepath, content, "python")
    imports = python_imports(tree)
    module = module_name(filepath)
    chunks: list[ASTChunk] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            class_content = _class_body_without_methods(lines, node) or _slice(lines, _node_start(node), getattr(node, "end_lineno", _node_start(node)))
            qualified = f"{module}.{class_name}" if module else class_name
            chunks.append(ASTChunk(
                filepath=filepath,
                content=class_content,
                lang="python",
                chunk_type="class",
                symbol_name=class_name,
                qualified_name=qualified,
                parent_symbol="",
                line_start=_node_start(node),
                line_end=getattr(node, "end_lineno", _node_start(node)),
                docstring=python_docstring(node),
                imports=imports,
                calls=python_calls(node),
                is_public=_public(class_name),
                content_hash=content_hash(class_content),
            ))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_name = f"{class_name}.{child.name}"
                    method_content = _slice(lines, _node_start(child), getattr(child, "end_lineno", _node_start(child)))
                    chunks.append(ASTChunk(
                        filepath=filepath,
                        content=method_content,
                        lang="python",
                        chunk_type="method",
                        symbol_name=method_name,
                        qualified_name=f"{module}.{method_name}" if module else method_name,
                        parent_symbol=class_name,
                        line_start=_node_start(child),
                        line_end=getattr(child, "end_lineno", _node_start(child)),
                        docstring=python_docstring(child),
                        imports=imports,
                        calls=python_calls(child),
                        is_public=_public(child.name),
                        content_hash=content_hash(method_content),
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_content = _slice(lines, _node_start(node), getattr(node, "end_lineno", _node_start(node)))
            chunks.append(ASTChunk(
                filepath=filepath,
                content=func_content,
                lang="python",
                chunk_type="function",
                symbol_name=node.name,
                qualified_name=f"{module}.{node.name}" if module else node.name,
                parent_symbol="",
                line_start=_node_start(node),
                line_end=getattr(node, "end_lineno", _node_start(node)),
                docstring=python_docstring(node),
                imports=imports,
                calls=python_calls(node),
                is_public=_public(node.name),
                content_hash=content_hash(func_content),
            ))
    if not chunks:
        from ragd_chunker.chunker import _module_chunk
        return _module_chunk(filepath, content, "python")
    return chunks
