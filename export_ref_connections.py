"""This is a first draft template that could be used to retrieve the edits on referenced nodes that define a look
Next step would be to filter the edits of interest, like shader assignments, sets they are added to, attributes that were added or changed in value.
Then we need to store these changes in a format that is artist-friendly and can be re-applied in another scene.
"""

import maya.cmds as mc
from collections import defaultdict
from pprint import pprint

def parse_mel_cmd(melStr):
    """Return the command, args and kwargs for a MEL command string"""

    # Get python variant and split of pymel import line
    import pymel.tools.mel2py as mel2py
    pyCmd = mel2py.mel2pyStr(melStr)
    pyCmd = pyCmd.splitlines()[1]
    print pyCmd

    cmd, arguments = pyCmd.split("(", 1)
    args, kwargs = eval("dummy" + "".join(pyCmd.partition("(")[1:]), {}, dict(dummy=lambda *x, **y: (x, y)))

    # return {'cmd': cmd,
    #         'args': args,
    #         'kwargs': kwargs}

def extract_edits(node, proxy):
    """Return a dictionary of data related to the look

    The given `nodes` must all be referenced nodes.

    Arguments:
        nodes (list): The nodes to retrieve the edits for.
    Returns:
        dict: Dictionary holding the edits to the nodes
            that define the look.
    """

    # Only allow referenced nodes
    # assert all(mc.referenceQuery(n, isNodeReferenced=True) for n in nodes)

    # Store each node per reference node they belong to
    ref_nodes = defaultdict(list)

    # for node in nodes:
    ref = mc.referenceQuery(node, referenceNode=True)
    ref_nodes[ref].append(node)

    # Get the reference edits for per reference node
    ref_edits = {}
    new_nodes = {}
    for ref in ref_nodes:
        # All succesfull edits with their long names
        edits = mc.referenceQuery(ref,
                                  editStrings=True,
                                  showNamespace=True,
                                  showDagPath=True,
                                  failedEdits=False)
        edit_nodes = mc.referenceQuery(ref,
                                  editNodes=True,
                                  showNamespace=True,
                                  showDagPath=True,
                                  failedEdits=False)
        ref_edits[ref] = edits
        new_nodes[ref] = edit_nodes

    # Filter edits to those that apply solely to our
    # subset of nodes instead of all that are in the
    # referenced scene.
    for ref, nodes in ref_nodes.iteritems():
        edits = ref_edits[ref]
        nodes = set(new_nodes[ref])
        for edit in edits:
            # TODO: Filter to edits that belong to 'nodes'
            # TODO: Filter the edits we actually want?
            pyCmd = parse_mel_cmd(edit + ';')
            print pyCmd['args'][0].split('.')[0]
            print str(pyCmd['cmd']) + '(' + str(pyCmd['args']) + ')' + str(pyCmd['kwargs'])
        for node in nodes:
            pass
            # print node

def make_proxy(nodes):
    for node in nodes:
        # print node
        proxy = mc.polyCube(n=(node + '_proxy'))[0]
        extract_edits(node, proxy)



if __name__ == "__main__":
    extract_edits(mc.ls(sl=1), '')
