import tomllib
import os
import subprocess
from subprocess import PIPE
from shlex import quote
import json
import tempfile
from dataclasses import dataclass
import csv
import argparse

BASE = os.path.dirname(__file__)
GRAPHS_TOML = os.path.join(BASE, "graphs.toml")
GRAPHS_DIR = os.path.join(BASE, "graphs")

SOME_GRAPHS = ['test.lpa', 'test.chr6c4', 'hprc.chrM']
ODGI = 'odgi'
FGFA = 'fgfa'


def check_wait(popen):
    err = popen.wait()
    if err:
        raise subprocess.CalledProcessError(err, popen.args)


@dataclass(frozen=True)
class HyperfineResult:
    command: str
    mean: float
    stddev: float
    median: float
    min: float
    max: float

    @classmethod
    def from_json(cls, obj):
        return cls(
            command=obj['command'],
            mean=obj['mean'],
            stddev=obj['stddev'],
            median=obj['median'],
            min=obj['min'],
            max=obj['max'],
        )


def hyperfine(cmds):
    """Run Hyperfine to compare the commands."""
    with tempfile.NamedTemporaryFile(delete_on_close=False) as tmp:
        tmp.close()
        subprocess.run(
            ['hyperfine', '-N', '--export-json', tmp.name] + cmds,
            check=True,
        )
        with open(tmp.name, 'rb') as f:
            data = json.load(f)
            return [HyperfineResult.from_json(r) for r in data['results']]


def graph_path(name, ext):
    return os.path.join(GRAPHS_DIR, f'{name}.{ext}')


def fetch_file(name, url):
    os.makedirs(GRAPHS_DIR, exist_ok=True)
    dest = graph_path(name, 'gfa')
    # If the file exists, don't re-download.
    if os.path.exists(dest):
        return

    if url.endswith('.gz'):
        # Decompress the file while downloading.
        with open(dest, 'wb') as f:
            curl = subprocess.Popen(['curl', '-L', url], stdout=PIPE)
            gunzip = subprocess.Popen(['gunzip'], stdin=curl.stdout, stdout=f)
            curl.stdout.close()
            check_wait(gunzip)
    else:
        # Just fetch the raw file.
        subprocess.run(['curl', '-L', '-o', dest, url], check=True)


def fetch_graphs(graphs, names):
    for graph_name in names:
        suite, key = graph_name.split('.')
        url = graphs[suite][key]
        fetch_file(graph_name, url)


def odgi_convert(name):
    """Convert a GFA to odgi's `.og` format."""
    og = graph_path(name, 'og')
    if os.path.exists(og):
        return

    gfa = graph_path(name, 'gfa')
    subprocess.run([ODGI, 'build', '-g', gfa, '-o', og])


def flatgfa_convert(name):
    """Convert a GFA to the FlatGFA format."""
    flatgfa = graph_path(name, 'flatgfa')
    if os.path.exists(flatgfa):
        return

    gfa = graph_path(name, 'gfa')
    subprocess.run([FGFA, '-I', gfa, '-o', flatgfa])


def compare_paths(name):
    """Compare odgi and FlatGFA implementations of path-name extraction.
    """
    og = graph_path(name, 'og')
    flatgfa = graph_path(name, 'flatgfa')
    odgi_cmd = f'odgi paths -i {quote(og)} -L'
    fgfa_cmd = f'fgfa -i {quote(flatgfa)} paths'

    results = hyperfine([odgi_cmd, fgfa_cmd])
    for cmd, res in zip(['odgi paths', 'fgfa paths'], results):
        yield {
            'cmd': cmd,
            'mean': res.mean,
            'stddev': res.stddev,
            'graph': name,
        }


def run_bench(out_csv):
    with open(GRAPHS_TOML, 'rb') as f:
        graphs = tomllib.load(f)
    fetch_graphs(graphs, SOME_GRAPHS)

    with open(out_csv, 'w') as f:
        writer = csv.DictWriter(f, ['graph', 'cmd', 'mean', 'stddev'])
        writer.writeheader()
        for graph in SOME_GRAPHS:
            odgi_convert(graph)
            flatgfa_convert(graph)
            for row in compare_paths(graph):
                writer.writerow(row)


def bench_main():
    parser = argparse.ArgumentParser(description='benchmarks for GFA stuff')
    parser.add_argument('--output', '-o', help='output CSV', required=True)
    args = parser.parse_args()
    run_bench(out_csv=args.output)


if __name__ == "__main__":
    bench_main()
