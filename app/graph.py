"""Reasoning graph utilities."""

from __future__ import annotations

from typing import Literal

GraphStage = Literal["ingestion", "researcher", "red_team", "synthesizer", "complete"]


def _dot_header() -> str:
    return "digraph reasoning {\n  rankdir=LR;\n  node [fontsize=12];\n"


def _node(name: str, color: str) -> str:
    safe_name = name.replace(" ", "")
    return f'{safe_name} [label="{name}", shape=box, style="filled", color="{color}", fontcolor="white"]'


def build_reasoning_graph(stage: GraphStage = "ingestion") -> str:
    """Return Graphviz DOT string for a given pipeline stage."""
    dot = _dot_header()
    nodes = []
    edges = []

    nodes.append(_node("Ingestion", "#5f6368"))
    if stage in {"researcher", "red_team", "synthesizer", "complete"}:
        nodes.append(_node("Researcher", "#4C8BF5"))
        edges.append("Ingestion -> Researcher")
    if stage in {"red_team", "synthesizer", "complete"}:
        nodes.append(_node("Red Team", "#EA4335"))
        edges.append("Researcher -> RedTeam")
    if stage in {"synthesizer", "complete"}:
        nodes.append(_node("Synthesizer", "#F9AB00"))
        edges.append("RedTeam -> Synthesizer")
        nodes.append(_node("Action Planner", "#A142F4"))
        edges.append("Synthesizer -> ActionPlanner")

    dot += "  " + ";\n  ".join(nodes) + ";\n"
    if edges:
        dot += "  " + ";\n  ".join(edges) + ";\n"
    dot += "}\n"
    return dot
