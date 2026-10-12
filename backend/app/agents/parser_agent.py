"""Parser Agent -- as of Step 9, this is a thin adopter, not a parser.

Architectural correction made in Step 9: Tree-sitter/AST parsing now
happens ONCE during repository ingestion (app/tasks/repository_ingestion_
tasks.py), persisted as ParsedSymbol rows. This node just receives that
already-computed data and shapes it into the graph's ParsedSymbols format
-- it does not call Tree-sitter itself, and it is DB-free like every other
agent (the DB read happens in documentation_tasks.py, which passes the
result down through the Orchestrator, mirroring exactly how
repository_analyzer_agent already receives pre-fetched file_tree/
manifest_contents rather than fetching them itself).

This also means the node basically never "fails" in the way the original
Step 4 design worried about (a bad file breaking the whole parse) --
per-file parse failures are now handled and logged during ingestion,
before generation ever runs.
"""

from app.agents.state import DocumentationGraphState, ParsedSymbols


async def run_parser_agent(
    state: DocumentationGraphState, precomputed_symbols: ParsedSymbols
) -> dict:
    """Returns {"parsed_symbols": precomputed_symbols}, verbatim. Kept as
    an async graph node (rather than inlining this into the Orchestrator)
    so the graph's shape -- analyzer -> parser -> fan-out -- stays
    self-documenting, and so a future change (e.g. re-deriving symbols
    on-the-fly for a repository ingested before this table existed) has
    an obvious single place to land.
    """
    return {"parsed_symbols": precomputed_symbols}
