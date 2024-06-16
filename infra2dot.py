import re
import sys
import pprint

#VERSION 1.1
#
# TODO:
#     Use the "Closer" section for invisible connections. E.g.:
#          Closer
#              node1 -- node2
#
#     Set label from quoted attributes like:
#          SoftOne("SoftOne App Service\nSoftOne Cloud Agent")
#
#     Make nets like this ....> dashed
#
#     Show arrows based on:
#           node1 ---> node2
#           node1 <--- node2
#           node1 ---- node2
#
#     Support attributes for Nets like this: 
#           node1 --(red "experimental")--> node2              # red colored connection labeled "experimental"
#           node1 --(10)--> node2                       # weight=10
#           node1 ("10.1.11.1")---->("10.1.11.5") node2 # labels at the edges
#
#     Print warnings for easy to make mistakes E.g.
#          sections with invalid name (e.g. "Hoosts")
#          invalid lines anywhere (e.g. in connections not having -- or having 3 nodes etc
#          nodes that are not connected anywhere
#          nodes that appear twice in the same section 
#          nodes that appear twice in non-compatible sections (e.g. in WebServices & Databases)
#
#     Support multiple nodes in a Net:
#           node1 -- node2 -- node3
#
#******************************************
ALL_NODES = {}
ALL_NETS = []
GND_NODES = []
GND_NODE_COUNTERS = {}
DB_NODES = []
WEB_NODES = []

class Node:
    def __init__(self, id):
        self.id = id
        self.label = ""
        self.attributes = []
        self.children_ids = []
        self.parent_id = ""

    def iterate_children(self):
        for child_id in self.children_ids:
            yield ALL_NODES[child_id]

    def children_count(self):
        return len(self.children_ids)

    def __repr__(self):
        attributes = [i[:5] for i in self.attributes]
        parent_info = f"{self.parent_id}/" if self.parent_id else ""
        return f"{parent_info}{self.id}({attributes})"

class Net:
    def __init__(self, left_node_id, right_node_id, net_name, net_style):
        self.left_node_id = left_node_id
        self.right_node_id = right_node_id
        self.net_name = net_name
        self.net_style = net_style
        self.attributes = []

    def __repr__(self):
        return f"{self.left_node_id}{self.net_style*2}{self.net_name}{self.net_style*2}{self.right_node_id}"

def extract_between_underscores(input_string):
    parts = input_string.split('_')
    if len(parts) < 3:
        return None
    return '_'.join(parts[1:-1])

def approximate_string_width(input_string):
    # Approximate widths in pixels for different character types
    widths = {
        'uppercase': 8,      # General width for uppercase letters
        'lowercase': 6,      # General width for lowercase letters
        'wide_uppercase': 10, # Wider uppercase letters like 'W', 'M'
        'narrow_lowercase': 4 # Narrow lowercase letters like 'i', 'l'
    }
    
    # Sets of characters for different width categories
    wide_uppercase_chars = {'W', 'M'}
    narrow_lowercase_chars = {'i', 'l', 'j', 't'}
    
    total_width = 0
    
    for char in input_string:
        if char in wide_uppercase_chars:
            total_width += widths['wide_uppercase']
        elif char.isupper():
            total_width += widths['uppercase']
        elif char in narrow_lowercase_chars:
            total_width += widths['narrow_lowercase']
        elif char.islower():
            total_width += widths['lowercase']
        else:
            # Default width for other characters (e.g., digits, punctuation)
            total_width += widths['lowercase']
    
    return total_width*8/340

def id_to_quoted_label(x):
    """
    preetify id for use as a label 
    E.g. by replacing __ with \n and _ with space
    """
    return x.replace("__","\\n").replace("_"," ").replace('_and_','&').replace('_slash_','/')

def id_to_html_label(x):
    """
    preetify id for use as a label 
    E.g. by replacing __ with <br/> and _ with space
    """
    return x.replace("__","<br/>").replace("_"," ").replace('_and_','&amp;').replace('_slash_','/')

def parse_node_line(line):
    """
    Parse a line to extract node IDs and their attributes.
    
    Parameters:
    line (str): A line of text containing node definitions. E.g.:
        node1(attr1) node2
        
    Returns:
    list of tuples: E.g.:
        [('node1', '(attr1)'),('node2', '')]
    """
    id_attr_pattern = r'([a-zA-Z_]\w*)(\s*(\[.*?\]|\(.*?\))?)'
    matches = re.findall(id_attr_pattern, line.strip())
    nodes = [(match[0], match[2].strip()) for match in matches]
    return nodes

def parse_attributes(attributes_str):
    """
    Parse an attribute string to extract individual attributes.
    
    Parameters:
    attributes_str (str): A string containing attributes.
    
    Returns:
    list of str: A list of attributes.
    """
    attributes = []
    if attributes_str:
        if attributes_str.startswith('['):
            attributes = re.findall(r'"[^"]*"|\w+', attributes_str.strip('[]'))
        elif attributes_str.startswith('('):
            attributes = re.findall(r'\w+', attributes_str.strip('()'))
    return attributes

def remove_comments(line):
    """
    Remove comments from a line of text, ignoring comments inside quoted attributes.
    
    Parameters:
    line (str): A line of text that may contain comments.
    
    Returns:
    str: The line with comments removed.
    """
    in_quotes = False
    new_line = []
    i = 0
    while i < len(line):
        if line[i] == '"':
            in_quotes = not in_quotes
            new_line.append(line[i])
        elif line[i:i+2] == '//' and not in_quotes:
            break
        else:
            new_line.append(line[i])
        i += 1
    return ''.join(new_line)

def process_node_definitions_text(lines):
    """
    Process lines of hierarchical text to build node definitions 
    and their hierarchy. NOT SUITABLE FOR CONNECTIONS
    
    Parameters:
    lines (list of str): Lines of text containing node definitions.
    """
    parent_stack = []
    indent_stack = []

    last_leading_spaces = 0
    indent_level = 0
    for line in lines:
        line = remove_comments(line)
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # indent_level
        leading_spaces = len(line) - len(line.lstrip(' '))
        if leading_spaces > last_leading_spaces:
            indent_level += 1
        elif leading_spaces < last_leading_spaces:
            indent_level -= 1
        last_leading_spaces = leading_spaces
        
        nodes = parse_node_line(stripped_line)
        # nodes is like this: [('node1', '(attr1)'),('node2', ''),...]    (often one tuple only)
        if not nodes:
            continue

        if indent_level==0 and len(nodes)==1:
            section = nodes[0][0] # [0] first node, [0] the node_id without the attributes
            print(f"BEGIN OF section {section} at indent_level {indent_level}")
        print(f"    {indent_level} {nodes}")
        for i, (id, attributes_str) in enumerate(nodes):
            if indent_level == 1 and (section=="Clusters" or section=="Hosts"):
                node_id = section[:4] + "_" + id
            else:
                node_id =  id
            if node_id not in ALL_NODES:
                ALL_NODES[node_id] = Node(node_id)

            node = ALL_NODES[node_id]
            node.attributes = parse_attributes(attributes_str)
            node.label = id_to_html_label(id)
            if section=='Databases' and indent_level>0:
                DB_NODES.append(node_id)
            if section=='WebServices' and indent_level>0:
                WEB_NODES.append(node_id)

            if indent_level == 0 and i == 0:
                parent_stack = [node_id]
                indent_stack = [indent_level]
                node.parent_id = ""
            else:
                while indent_stack and indent_stack[-1] >= indent_level:
                    parent_stack.pop()
                    indent_stack.pop()

                if parent_stack:
                    parent_id = parent_stack[-1]
                    parent_node = ALL_NODES[parent_id]
                    node.parent_id = parent_id
                    parent_node.children_ids.append(node_id)

                parent_stack.append(node_id)
                indent_stack.append(indent_level)
            print(node)

def process_net_line(line):
    """
    Process a single line from the connections section and append a Net instance to ALL_NETS.
    
    Parameters:
    line (str): A line of text from the connections section.
    """
    net_pattern = r'([a-zA-Z_]\w*)\s*([-.]+[a-zA-Z0-9_]*[-.>]+)\s*([a-zA-Z_]\w*)'
    match = re.match(net_pattern, line.strip())
    if match:
        left_node_id = match.group(1)
        connector = match.group(2)
        right_node_id = match.group(3)

        # Extract net_style and net_name from connector
        if '-' in connector:
            net_style = '-'
        else:
            net_style = '.'

        net_name_match = re.search(r'[-.]+([a-zA-Z0-9_]*?)[-.>]+$', connector)
        net_name = net_name_match.group(1) if net_name_match else ""

        net = Net(left_node_id, right_node_id, net_name, net_style)
        ALL_NETS.append(net)

def preprocess_nets_text(nets_text):
    """
    Process nets_text to handle GND nodes, replacing them with unique identifiers.
    
    Parameters:
    nets_text (list of str): Lines of text containing connections.
    
    Returns:
    list of str: The modified nets_text with unique identifiers for GND nodes.
    """
    global GND_NODE_COUNTERS
    gnd_pattern = r'/([a-zA-Z_]\w*)/'
    modified_nets_text = []
    
    #print(f"nets_text before preprocess_nets_text:\n\n{''.join(nets_text)}\n")
    # Collect all GND nodes
    for line in nets_text:
        matches = re.findall(gnd_pattern, line)
        for match in matches:
            if not(match in GND_NODES):
                GND_NODES.append(match)
    
    print(f"Found GND node {GND_NODES}")
    GND_NODE_COUNTERS = {gnd: 1 for gnd in GND_NODES}
    
    # Replace occurrences of GND nodes with unique identifiers
    for line in nets_text:
        modified_line = line
        for gnd in GND_NODES:
            gnd_full = f'/{gnd}/'
            if gnd_full in line:
                unique_gnd = f'xg_{gnd}_{GND_NODE_COUNTERS[gnd]}'
                modified_line = modified_line.replace(gnd_full, unique_gnd, 1)
                GND_NODE_COUNTERS[gnd] += 1
        modified_nets_text.append(modified_line)
    
    print(f"nets_text before preprocess_nets_text:\n\n{''.join(modified_nets_text)}\n")
    return modified_nets_text

def process_nets_text(lines):
    """
    Process lines of text in the connections section.
    
    Parameters:
    lines (list of str): Lines of text containing connections.
    """
    if lines:
        section_type = lines[0].strip().lower()
        for line in lines[1:]:
            process_net_line(line)

def process_input(lines):
    """
    Process the entire input to separate node definitions and connections sections.
    
    Parameters:
    lines (list of str): The entire input text as lines of text.
    """
    nodes_text = []
    nets_text = []
    in_nets_section = False

    for line in lines:
        if re.match(r'^Connections\s*', line):
            in_nets_section = True
            nets_text.append(line)
        elif in_nets_section and not line.startswith(' '):
            in_nets_section = False
        if in_nets_section:
            nets_text.append(line)
        else:
            nodes_text.append(line)

    process_node_definitions_text(nodes_text)
    if nets_text:
        nets_text = preprocess_nets_text(nets_text)
        process_nets_text(nets_text)

def main():
    """
    The main function to handle file input/output and initiate processing.
    """
    if len(sys.argv) != 5:
        print("Usage(1): python infra2dot.py -f input.txt -t output.dot")
        return

    input_flag = sys.argv[1]
    input_file = sys.argv[2]
    output_flag = sys.argv[3]
    output_file = sys.argv[4]

    if input_flag != '-f' or output_flag != '-t':
        print("Usage(2): python infra2dot.py -f input.txt -t output.dot")
        return

    with open(input_file, 'r') as file:
        lines = file.readlines()

    process_input(lines)


    with open(output_file, 'w') as file:
        file.write('''digraph G {
    fontname="Arial" // Graph attributes
    // default node & edge properties
    node [shape=box, style=filled, fontname="Arial", fontcolor=black, fillcolor=palegreen]
    edge [dir=none]

    // GND nodes 
    { node [shape=parallelogram, fixedsize=true, height=0.3, fontcolor=white]
''')

        GND_colors = ["#364895","#cd6900","#4444ff","#a52a2a","#a90053"]
        GND_node_color = {}
        for i, gnd_node in enumerate(GND_NODES):
            color = GND_colors[i % len(GND_colors)]
            GND_node_color[gnd_node] = color
            width = int(approximate_string_width(gnd_node)*100)/100
            file.write(f'        {{node [label="{gnd_node}", width={width}, color="{color}", fillcolor="{color}"]')
            file.write('\n          ')
            for i in list(range(1, GND_NODE_COUNTERS[gnd_node] )):
                file.write(f'xg_{gnd_node}_{i} ')
            file.write(' }\n')
        file.write('    }\n')

        if DB_NODES: 
            file.write('''    // Databases
    { node [fillcolor="#CDE8F6", shape=cylinder]
''')                
            for node_id in DB_NODES:
                node = ALL_NODES[node_id]
                file.write(f'        {node.id}  [label="\\n{node.label}"]\n')
            file.write('    }\n')


        if WEB_NODES: 
            file.write('''    // Web visible services
    { node [fillcolor="#00ffcc"]
''')                
            for node_id in WEB_NODES:
                node = ALL_NODES[node_id]
                file.write(f'        {node.id}  [label="{node.label}\\n(https)"]\n')
            file.write('    }\n')


        file.write('''    // VPN Nodes
    { node [shape=cds, fixedsize=true, width=0.9, height=0.7, style=filled, fillcolor="#ddccff",  color="#732375"]
''')

        # detect VPNs
        all_vpns=[]
        all_vpn_counters={}
        for net in ALL_NETS:
            name = net.net_name
            if name:
                if name in all_vpns:
                    all_vpn_counters[name] += 1
                else:
                    all_vpns.append(name)
                    all_vpn_counters[name] = 1
        #pprint.pprint(all_vpns)
        #pprint.pprint(all_vpn_counters)

        for vpn in all_vpns:
            file.write(f'        node [label="{vpn}\\nVPN"]  {{')
            for i in list(range(1, all_vpn_counters[vpn] + 1)):
                file.write(f"xv_{vpn}_{i}  ")
            file.write('}\n')
        file.write('    }\n')

        file.write('''    // Clusters (groups of devices)\n''')
        #print()
        #print('CLUSTERS')
        empty_clusters = []
        found_clusters = False
        for n in ALL_NODES:
            node = ALL_NODES[n]
            if node.parent_id=="Clusters":
                #print(node)
                if node.children_count()>0:
                    cluster_id = node.id[5:] # removes the Clus_ prefix
                    file.write(f'    subgraph cluster_{cluster_id} {{\n')
                    file.write(f'        style = filled; color = "lightgray"; label = <<b>{id_to_html_label(cluster_id)}</b>>; fontsize=18\n')
                    found_clusters = True
                    for cid in node.children_ids:
                        #print(ALL_NODES[cid])
                        if ALL_NODES[cid].label != ALL_NODES[cid].id:
                            file.write(f'        {ALL_NODES[cid].id} [label=<{ALL_NODES[cid].label}>]\n')
                        else:
                            file.write(f'        {ALL_NODES[cid].id}\n')
                    file.write('    }\n')
                else:
                    empty_clusters.append(node)
                    print(f'CLUSTER WITHOUT CHILDREN: {node}')
        if empty_clusters:
            file.write('''    // Empty Clusters (nodes that have the appearance of Clusters)\n''')
            file.write('    { node [fontsize=18, fillcolor=lightgray, color=lightgray]\n')
            for node in empty_clusters:
                file.write(f'        {node.id[5:]} [label=<<b>{node.label}</b><br/><br/> . >]\n') # [5:] removes the Clus_ prefix
            file.write('    }\n')

        file.write('''    // Hosts/Devices/Servers/HW offering services\n''')
        #print()
        #print('HOSTS')
        found_hosts = False
        for n in ALL_NODES:
            node = ALL_NODES[n]
            if node.parent_id=="Hosts":
                #print(node)
                host_id = node.id[5:] # removes the Host_ prefix
                if 'azure' in host_id.lower():
                    color="lightblue"
                else:
                    color="#ffa6bb"
                file.write(f'    subgraph cluster_{host_id} {{\n')
                file.write(f'        style = filled; color ="{color}"; label = < <b>{id_to_html_label(host_id)}</b> >\n')
                found_hosts = True
                for cid in node.children_ids:
                    #print(ALL_NODES[cid])
                    if ALL_NODES[cid].label != ALL_NODES[cid].id:
                        file.write(f'        {ALL_NODES[cid].id} [label=<{ALL_NODES[cid].label}>]\n')
                    else:
                        file.write(f'        {ALL_NODES[cid].id}\n')
                file.write('    }\n')
        if found_hosts: 
            file.write('''    //end of hosts\n\n''')


        file.write('''    // Nets (connections)\n''')
        file.write('''{edge [color="#00000080" penwidth=2.0]''')
        for vpn in all_vpns:
            all_vpn_counters[vpn] = 1 
        for net in ALL_NETS:
            if net.net_name:
                x_vpn_i = f"xv_{net.net_name}_{all_vpn_counters[net.net_name]}"
                all_vpn_counters[net.net_name] += 1
                file.write(f'    {net.left_node_id} -> {x_vpn_i} [color="#bbaaddb0" penwidth=4.0]\n')
                file.write(f'    {x_vpn_i} -> {net.right_node_id} [color="#bbaaddb0" penwidth=4.0]\n')
            else:
                color = None
                if net.left_node_id.startswith('xg_'):
                    color = GND_node_color[extract_between_underscores(net.left_node_id)]
                elif net.right_node_id.startswith('xg_'):
                    color = GND_node_color[extract_between_underscores(net.right_node_id)]
                if color:
                    file.write(f'    {net.left_node_id} -> {net.right_node_id} [color="{color}a0" penwidth=2.0]\n')
                else:
                    file.write(f'    {net.left_node_id} -> {net.right_node_id}\n')
            
        # end of file
        file.write('}}\n')
        
    #pprint.pprint(all_vpns)

def test():
    sys.argv = sys.argv + ['-f','test.infra','-t','test-infra.dot']
    main()
    
if __name__ == "__main__":
    main()
    
