"""Preprocessing functions for mygfa."""

from typing import List, Tuple, Dict
from . import mygfa


def node_steps(graph):
    """For each segment in the graph,
    list the times the segment was crossed by a path"""
    # segment name, (path name, index on path, direction) list
    crossings: Dict[str, List[Tuple[str, int, bool]]] = {}
    for segname in graph.segments.keys():
        crossings[segname] = []

    for path in graph.paths.values():
        for index, handle in enumerate(path.segments):
            crossings[handle.name].append((path.name, index, handle.ori))

    return crossings


def adjlist(graph):
    """Construct an adjacency list representation of the graph.
    This is via two dicts having the same type:
    key: Handle              # my details
    value: list of Handle    # neighbors' details
    We take each segment into account, regardless of whether it is on a path.
    We make two such dicts: one for in-edges and one for out-edges
    """
    ins: Dict[mygfa.Handle, List[mygfa.Handle]] = {}
    outs: Dict[mygfa.Handle, List[mygfa.Handle]] = {}
    for segname in graph.segments.keys():
        ins[mygfa.Handle(segname, True)] = []
        ins[mygfa.Handle(segname, False)] = []
        outs[mygfa.Handle(segname, True)] = []
        outs[mygfa.Handle(segname, False)] = []

    for link in graph.links:
        ins[link.to_].append(link.from_)
        outs[link.from_].append(link.to_)

    return (ins, outs)


def handle_seq(graph, handle):
    """Get the sequence of a handle, reverse-complementing if necessary."""
    seg = graph.segments[handle.name]
    return seg.seq if handle.ori else seg.revcomp().seq


def pathseq(graph):
    """Given a graph, precompute the _sequence_
    charted by each of the graph's paths.
    """
    ans = {}
    for path in graph.paths.keys():
        ans[path] = "".join(
            handle_seq(graph, handle) for handle in graph.paths[path].segments
        )
    return ans


def get_maxes(graph):
    """Return the maximum number of nodes, steps, and paths in the graph."""
    max_nodes = len(graph.segments)
    max_steps = max([len(steps) for steps in node_steps(graph).values()])
    max_paths = len(graph.paths)
    return max_nodes, max_steps, max_paths


def drop_all_overlaps(paths):
    """Drop all overlaps from the given paths."""
    return {name: path.drop_overlaps() for name, path in paths.items()}
