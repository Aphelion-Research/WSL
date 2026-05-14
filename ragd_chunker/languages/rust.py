from ragd_chunker.chunker import _module_chunk

def chunk_rust(filepath: str, content: str):
    return _module_chunk(filepath, content, "rust")
