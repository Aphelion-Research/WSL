from ragd_chunker.chunker import _module_chunk

def chunk_typescript(filepath: str, content: str):
    return _module_chunk(filepath, content, "typescript")
