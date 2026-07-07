"""L4 Memory subsystem (architecture §4.3).

Multi-layer structured memory + retrieval (FTS + vector) + Ebbinghaus review +
compression/forgetting. Depends only on ``campus.memory.ports`` (pure Protocol),
never on a specific backend — backends (``InMemoryStore``, ``JsonFileStore``) live
beside the ports file.
"""
