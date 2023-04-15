import sys
import mygfa
import random
import preprocess


def print_bed(graph):
  """Creates a reasonable query for `inject`.
  Each entry of the output is of the form
    `name lo hi new_name`
  where
    `name` is the name of an existing path.
		`lo`/`hi` are the start/end points that we should walk over; lo <= hi.
		`new_name` is the name of the path we wish to create.
  """
  # random.seed(4)
  for path in graph.paths.values():
    length = len(preprocess.pathseq(graph)[path.name])
    for i in range(random.randint(0,5)):
      r1 = random.randint(0, length)
      r2 = random.randint(0, length)
      lo = str(min(r1, r2))
      hi = str(max(r1, r2))
      print ("\t".join([path.name, lo, hi, f"{path.name}_{i}"]))


if __name__ == "__main__":
    graph = mygfa.Graph.parse(sys.stdin)
    print_bed(graph)