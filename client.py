import zmq
import networkx as nx

class BNBTree:
    Tree = nx.Graph()
    root = None
    _incumbent_value = None
    _incumbent_parent = None

    def __init__(self):
        self.Tree = nx.Graph()
        self.root = None
        self._incumbent_value = None
        self._incumbent_parent = None

    def AddOrUpdateNode(self, id, parent_id, branch_direction, status, lp_bound,
                    integer_infeasibility_count, integer_infeasibility_sum,
                    condition_begin = None, condition_end = None,
                    **attrs):
        if id in self.Tree.nodes():
            # Existing node, update attributes
            self.Tree.nodes[id]["status"] = status
            self.Tree.nodes[id]["lp_bound"] = lp_bound
            self.Tree.nodes[id]["integer_infeasibility_count"] = integer_infeasibility_count
            self.Tree.nodes[id]["integer_infeasibility_sum"] = integer_infeasibility_sum
        elif self.root is None:
            self.root = 0
            print('Adding root', id)
            self.Tree.add_node(0)
            self.Tree.add_node(id)
            self.Tree.add_edge(0,id)
            self.Tree.nodes[id]["direction"] = branch_direction

        elif parent_id is not None:
            if branch_direction == "R":
                if (len([n for n in self.Tree[parent_id]]) > 3):
                    raise RuntimeError("Tree is not binary").with_traceback(sys.exec_info())
                for neighbor in self.Tree[parent_id]:
                    if (neighbor > parent_id and self.Tree.nodes[neighbor]["direction"] == "R"):
                        raise RuntimeError("Sibling node has matching branch direction").with_traceback(sys.exec_info())
                self.Tree.add_node(id)
                self.Tree.add_edge(id, parent_id)
                self.Tree.nodes[id]["direction"] = "R"
            if branch_direction == "L":
                if (len([n for n in self.Tree[parent_id]]) > 3):
                    raise RuntimeError("Tree is not binary").with_traceback(sys.exec_info())
                for neighbor in self.Tree[parent_id]:
                    if (neighbor > parent_id and self.Tree.nodes[neighbor]["direction"] == "L"):
                        raise RuntimeError("Sibling node has matching branch direction").with_traceback(sys.exec_info())
                self.Tree.add_node(id)
                self.Tree.add_edge(id, parent_id)
                self.Tree.nodes[id]["direction"] = "L"
        else:
            print("Some kind of fall through?")

    def ProcessLine(self, line):
        line = line.strip()
        if line[0] == "#":
            return
        tokens = line.split()
        if len(tokens) < 3:
            raise SyntaxError('Incomplete or invalid line: %s' %' '.join(tokens)).with_traceback(sys.exec_info())
        # Tokens shared by all line types
        self._time = float(tokens[0])
        line_type = tokens[1]
        remaining_tokens = tokens[2:]

        node_id = int(tokens[2])
        parent_id = int(tokens[3])
        branch_direction = tokens[4]
        remaining_tokens = tokens[5:]
        if line_type == 'integer':
            self._optimal_soln_time = self._time
            self.ProcessIntegerLine(node_id, parent_id,
                                    branch_direction, remaining_tokens)
        elif line_type == 'fathomed':
            self.ProcessFathomedLine(node_id, parent_id,
                                     branch_direction, remaining_tokens)
        elif line_type == 'candidate':
            self.ProcessCandidateLine(node_id, parent_id,
                                      branch_direction, remaining_tokens)
        elif line_type == 'pregnant':
            self.ProcessPregnantLine(node_id, parent_id,
                                     branch_direction, remaining_tokens)
        elif line_type == 'branched':
            self.ProcessBranchedLine(node_id, parent_id,
                                     branch_direction, remaining_tokens)
        elif line_type == 'infeasible':
            self.ProcessInfeasibleLine(node_id, parent_id,
                                       branch_direction, remaining_tokens)
        else:
            raise TypeError('Unexpected line type "%s": %s' % (line_type,
                                                     ' '.join(tokens))).with_traceback(sys.exec_info())
    def ProcessIntegerLine(self, node_id, parent_id, branch_direction,
                           remaining_tokens):
        if len(remaining_tokens) != 1:
            raise RuntimeError('Invalid line: %s integer %s %s %s %s\nShould match: <time> integer <node id> <parent id>' % (
                    self._time, node_id, parent_id, branch_direction,
                    ' '.join(remaining_tokens))).with_traceback(sys.exec_info())
        objective_value = float(remaining_tokens[0])
        self.AddOrUpdateNode(node_id, parent_id, branch_direction, 'integer',
                             objective_value, None, None)
        self._previous_incumbent_value = self._incumbent_value
        self._incumbent_value = objective_value
        self._incumbent_parent = parent_id
        self._new_integer_solution = True

    def ProcessFathomedLine(self, node_id, parent_id, branch_direction,
                            remaining_tokens):
        # Print a warning if there is no current incumbent.
        if self._incumbent_value is None:
            raise SyntaxWarning('WARNING: Encountered "fathom" line before first incumbent.\nThis may indicate an error in the input file.').with_traceback(sys.exec_info())
        # Parse remaining tokens
        if len(remaining_tokens) > 1:
            raise RuntimeError('Invalid line: %s fathomed %s %s %s %s\nShould match: <time> fathomed <node id> <parent id>' % (
                    self._time, node_id, parent_id, branch_direction,
                    ' '.join(remaining_tokens))).with_traceback(sys.exec_info())
        if len(remaining_tokens) == 1:
            lp_bound = float(remaining_tokens[0])
        else:
            if (node_id in self.Tree.nodes() and
                self.Tree.nodes[node_id]["lp_bound"] is not None):
                lp_bound = self.Tree.nodes[node_id]["lp_bound"]
            else:
                lp_bound = self.Tree.nodes[parent_id]["lp_bound"]
        self.AddOrUpdateNode(node_id, parent_id, branch_direction, "fathomed", lp_bound, self.Tree.nodes[parent_id]["integer_infeasibility_count"], self.Tree.nodes[parent_id]["integer_infeasibility_sum"])

    def ProcessPregnantLine(self, node_id, parent_id, branch_direction,
                            remaining_tokens):
        # Parse remaining tokens
        if len(remaining_tokens) != 3:
            raise RuntimeError('Invalid line: %s pregnant %s %s %s %s\nShould match: <time> pregnant <node id> <parent id> \n<branch direction> <lp bound> \n<sum of integer infeasibilities> <number of integer \ninfeasibilities>' % (
                    self._time, node_id, parent_id, branch_direction,
                    ' '.join(remaining_tokens))).with_traceback(sys.exec_info())
        lp_bound = float(remaining_tokens[0])
        integer_infeasibility_sum = float(remaining_tokens[1])
        integer_infeasibility_count = int(remaining_tokens[2])

        self.AddOrUpdateNode(node_id, parent_id, branch_direction, 'pregnant',
                             lp_bound, integer_infeasibility_count,
                             integer_infeasibility_sum)

    def ProcessBranchedLine(self, node_id, parent_id, branch_direction,
                            remaining_tokens):
        # Parse remaining tokens
        if len(remaining_tokens) not in [3, 5]:
            raise RuntimeError('Invalid line: %s branched %s %s %s %s\nShould match: <time> branched <node id> <parent id> \n<branch direction> <lp bound> \n<sum of integer infeasibilities> <number of integer \ninfeasibilities>' % (
                    self._time, node_id, parent_id, branch_direction,
                    ' '.join(remaining_tokens))).with_traceback(sys.exec_info())
        lp_bound = float(remaining_tokens[0])
        integer_infeasibility_sum = float(remaining_tokens[1])
        integer_infeasibility_count = int(remaining_tokens[2])
        if len(remaining_tokens) == 5:
            # In this case, we must also be printing conditions numbers
            condition_begin = int(remaining_tokens[3])
            condition_end = int(remaining_tokens[4])
        self.AddOrUpdateNode(node_id, parent_id, branch_direction, 'branched',
                             lp_bound, integer_infeasibility_count,
                             integer_infeasibility_sum, condition_begin,
                             condition_end)

    def ProcessInfeasibleLine(self, node_id, parent_id, branch_direction,
                              remaining_tokens):
        # Parse remaining tokens
        if len(remaining_tokens) not in [0, 2]:
            raise RuntimeError('Invalid line: %s infeasible %s %s %s %s\nShould match: <time> infeasible <node id> <parent id> \n<branch direction>' % (
                    self._time, node_id, parent_id, branch_direction,
                    ' '.join(remaining_tokens))).with_traceback(sys.exec_info())
        # Use parent values if the node does not have its own
        lp_bound = self.Tree.nodes[parent_id]["lp_bound"]
        ii_count = self.Tree.nodes[parent_id]["integer_infeasibility_count"]
        ii_sum = self.Tree.nodes[parent_id]["integer_infeasibility_sum"]
        if node_id in self.Tree.nodes():
            if self.Tree.nodes[node_id]["lp_bound"] is not None:
                lp_bound = self.Tree.nodes[node_id]["lp_bound"]
            if self.Tree.nodes[node_id]["integer_infeasibility_count"] is not None:
                ii_count = self.Tree.nodes[node_id]["integer_infeasibility_count"]
            if self.Tree.nodes[node_id]["integer_infeasibility_sum"] is not None:
                ii_sum = self.Tree.nodes[parent_id]["integer_infeasibility_sum"]
        if len(remaining_tokens) == 2:
            # In this case, we must also be printing conditions numbers
            condition_begin = int(remaining_tokens[0])
            condition_end = int(remaining_tokens[1])
        self.AddOrUpdateNode(node_id, parent_id, branch_direction, 'infeasible',
                             lp_bound, ii_count, ii_sum)

    def ProcessCandidateLine(self, node_id, parent_id, branch_direction,
                             remaining_tokens):
        # Parse remaining tokens
        if len(remaining_tokens) == 2 or len(remaining_tokens) > 3:
            raise RuntimeError('Invalid line: %s branched %s %s %s %s\nShould match: <time> candidate <node id> <parent id> \n<branch direction> [<lp bound>] \n[<sum of integer infeasibilities> <number of integer \ninfeasibilities>]' % (
                    self._time, node_id, parent_id, branch_direction,
                    ' '.join(remaining_tokens))).with_traceback(sys.exec_info())
        if len(remaining_tokens) > 0:
            lp_bound = float(remaining_tokens[0])
        else:
            lp_bound = self.get_node_attr(parent_id, 'lp_bound')
        if len(remaining_tokens) == 3:
            integer_infeasibility_sum = float(remaining_tokens[1])
            integer_infeasibility_count = int(remaining_tokens[2])
        else:
            integer_infeasibility_sum = self.Tree.nodes[parent_id][
                                                  "integer_infeasibility_sum"]
            integer_infeasibility_count = self.Tree.nodes[parent_id][
                                                "integer_infeasibility_count"]
        self.AddOrUpdateNode(node_id, parent_id, branch_direction, 'candidate',
                             lp_bound, integer_infeasibility_count,
                             integer_infeasibility_sum)
    #def display(self, item = 'all', basename = 'graph', format='png', count=None,
    #            pause=False, wait_for_click=True):

    #def GenerateTreeImage(self, fixed_horizontal_positions = False):
port = 5555
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:" + str(port))
bt = BNBTree()

print("Connecting...")
while(True):
    socket.send_string("hello")

    msg = socket.recv_string()
    print(msg.rstrip().split(' '))
    if(msg == 'END'):
        break
    bt.ProcessLine(msg)

for n in bt.Tree.nodes.data():
    print(n)
print("end")
