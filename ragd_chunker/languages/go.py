from ragd_chunker.chunker import _module_chunk

def chunk_go(filepath: str, content: str):
    return _module_chunk(filepath, content, "go")
