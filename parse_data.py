'''
This file converts an odgi graph to numerical JSON data that can be used by calyx hardware simulators.
'''

import sys
import argparse
import json
import odgi

# Defaults for the maximum possible number of nodes, steps per node, and paths to consider
MAX_NODES=16
MAX_STEPS=15
MAX_PATHS=15

def parse_steps_on_nodes(graph, path_name_to_id, max_nodes=MAX_NODES, max_steps=MAX_STEPS, max_paths=MAX_PATHS):
    '''
    Generate input data containing the path ids for each step on each node in the graph, e.g.
    {path_ids1: 
        "data": [0, 1, 1, 2],
            "format": {
                "numeric_type": "bitnum",8kklkskl
                "is_signed": False,
                "width": 2
            }
    }
    '''

    num_nodes = graph.get_node_count()
    
    # Check that the number of steps on the node does not exceed max_steps
    if num_nodes > max_nodes:
        raise Exception(f'The number of nodes in the graph exceeds the maximum number of nodes the hardware can process. Hint: try setting the maximum number of nodes manually using the -n flag.')
    
    data = {}
    width = max_paths.bit_length()

    # Initialize the data for each node
    def parse_node(node_h):
        '''
        Get a list of path ids for each step on node_h.
        '''

        # Check that the number of steps on the node does not exceed max_steps
        if graph.get_step_count(node_h) > max_steps:
            raise Exception(f'The number of paths in the graph exceeds the maximum number of paths the hardware can process. {graph.get_step_count(node_h)} > {max_steps}. Hint: try setting the maximum number of steps manually using the -e flag.')
        
        path_ids = []

        def parse_step(step_h):
            path_h = graph.get_path(step_h)
            path_id = path_name_to_id[graph.get_path_name(path_h)]
            path_ids.append(path_id)
            
        graph.for_each_step_on_handle(node_h, parse_step)

        # Pad path_ids with 0s
        path_ids = path_ids + [0] * (max_steps + 1 - len(path_ids))
        
        # 'path_ids{id}' is the list of path ids for each step crossing node {id}
        node_id = graph.get_id(node_h)
        data[f'path_ids{node_id}'] = {
            "data": path_ids,
            "format": {
                "numeric_type": "bitnum",
                "is_signed": False,
                "width": width
            }
        }

    graph.for_each_handle(parse_node)

    default_steps = [0] * max_steps
    
    while num_nodes < max_nodes:
        num_nodes += 1
        data[f'path_ids{num_nodes}'] = {
            "data": default_steps,
            "format": {
                "numeric_type": "bitnum",
                "is_signed": False,
                "width": width
            }
        }
    
    return data


def parse_paths_file(filename, path_to_id, max_paths=MAX_PATHS):
    '''
    Return paths_to_consider, a list of length max_paths, where 
    paths_to_consider[i] is 1 if i is a path id and we include path i in our
    calculations of node depth
    '''
    
    if filename is None: # Return the default value
        paths_to_consider = [1]*(max_paths + 1)
        paths_to_consider[0] = 0
        return paths_to_consider

    with open(filename, 'r') as paths_file:
        text = paths_file.read()
        paths = text.splitlines()

    paths_to_consider = [0] * (max_paths + 1)
        
    for path_name in paths:
        path_id = path_name_to_id[path_name]
        paths_to_consider[path_id] = 1

    return paths_to_consider


if __name__ == '__main__':
    
    # Parse commandline arguments                                              
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='A .og file representing a pangenome whose node depth we want to calculate')
    parser.add_argument('-s', '--subset-paths', help='Specify a file containing a subset of all paths in the graph. See the odgi documentation for more details.')
    parser.add_argument('-n', '--max-nodes', type=int, default=MAX_NODES, help='Specify the maximum number of nodes that the hardware can support.')
    parser.add_argument('-e', '--max-steps', type=int, default=MAX_STEPS, help='Specify the maximum number of steps per node that the hardware can support.')
    parser.add_argument('-p', '--max-paths', type=int, default=MAX_PATHS, help='Specify the maximum number of paths that the hardware can support.')
    parser.add_argument('-o', '--out', help='Specify the output file. If not specified, will dump to stdout.')
    args = parser.parse_args()

    graph = odgi.graph()
    graph.load(args.filename)

    
    # Check that the number of paths on the graph does not exceed max_paths
    if graph.get_path_count() > args.max_paths:
        raise Exception(f'The number of paths in the graph exceeds the maximum number of paths the hardware can process. {graph.get_path_count()} > {args.max_paths}. Hint: try setting the maximum number of paths manually using the -p flag')

    # Assign a path_id to each path; the path_ids are not accessible using the
    # default python bindings for odgi
    
    # Obtain a list of path names; a path's index is its id
    paths = []
    graph.for_each_path_handle(lambda h: paths.append(graph.get_path_name(h)))
    
    # Path name -> path id                                                     
    path_name_to_id = {path:count for count, path in enumerate(paths)}

    
    paths_to_consider = parse_paths_file(args.subset_paths, path_name_to_id, args.max_paths)

    data = parse_steps_on_nodes(graph, path_name_to_id, args.max_nodes, args.max_steps, args.max_paths)

    data['paths_to_consider'] = {
        "data": paths_to_consider,
        "format": {
            "numeric_type": "bitnum",
            "is_signed": False,
            "width": 1
        }
    }

    data['depth_output'] = {
        "data": [0] * args.max_nodes,
        "format": {
            "numeric_type": "bitnum",
            "is_signed": False,
            "width": args.max_steps.bit_length()
        }
    }

    data['depth_uniq_output'] = {
        "data": [0] * args.max_nodes,
        "format": {
            "numeric_type": "bitnum",
            "is_signed": False,
            "width": args.max_paths.bit_length()
        }
    }

    if args.out:
        with open(args.out, 'w') as out_file:
            json.dump(data, out_file, indent=2, sort_keys=True)
    else:
        json.dump(data, sys.stdout, indent=2, sort_keys=True)
