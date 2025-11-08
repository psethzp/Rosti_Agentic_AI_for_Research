"""Reasoning graph utilities."""

from __future__ import annotations

from typing import List


def build_reasoning_graph(include_red_team: bool = False) -> str:
    """Return Graphviz DOT string for the reasoning pipeline."""
    nodes: List[str] = [
        'Researcher [shape=box, style="filled", color="#4C8BF5", fontcolor="white"]',
        'Reviewer [shape=box, style="filled", color="#34A853", fontcolor="white"]',
        'Synthesizer [shape=box, style="filled", color="#F9AB00", fontcolor="black"]',
    ]
    edges: List[str] = [
        "Researcher -> Reviewer",
        "Reviewer -> Synthesizer",
    ]
    if include_red_team:
        nodes.append('RedTeam [shape=box, style="filled", color="#EA4335", fontcolor="white"]')
        edges.extend(["Reviewer -> RedTeam", "RedTeam -> Synthesizer"])
    dot = "digraph reasoning {\n  rankdir=LR;\n  node [fontsize=12];\n"
    dot += "  " + ";\n  ".join(nodes) + ";\n"
    dot += "  " + ";\n  ".join(edges) + ";\n"
    dot += "}\n"
    return dot
