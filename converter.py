import networkx as nx
import re
import html
import math

# Constants for layout
FONT_SIZE = 14
CHAR_WIDTH_AVG = 8  # Approximate width of a character in pixels
LINE_HEIGHT = 20
PADDING_X = 10
PADDING_Y = 10
MIN_BLOCK_WIDTH = 100

def convert_mermaid_to_nsd(mermaid_content):
    graph, start_node = parse_mermaid(mermaid_content)
    if not start_node:
        return '<svg><text>Error: No start node found</text></svg>'
        
    structured_tree = build_structure(graph, start_node, None, set())
    
    # 1. Calculate Minimum Widths
    # We need to annotate the tree with min_width requirements
    total_min_width = calculate_min_widths(structured_tree)
    
    # Ensure a reasonable total width, but at least the min required
    width = max(800, total_min_width)
    
    # 2. Calculate Heights based on the actual width we will use
    # We pass the available width to calculate wrapping
    total_height = calculate_heights(structured_tree, width)
    
    svg_content = render_blocks(structured_tree, 0, 0, width)
    
    return f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">{svg_content}</svg>'

def parse_mermaid(content):
    G = nx.DiGraph()
    lines = content.split('\n')
    edge_pattern = re.compile(r'(.+?)\s*-->\s*(?:\|(.*?)\|\s*)?(.+)')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('graph') or line.startswith('%%') or line.startswith('subgraph'):
            continue
            
        if '-->' in line:
            parts = line.split('-->')
            left_part = parts[0].strip()
            right_part = parts[1].strip()
            
            left_id, left_label, left_type = parse_node_str(left_part)
            if left_id:
                if left_id not in G: G.add_node(left_id, label=left_label, type=left_type)
                
            edge_label = ""
            if right_part.startswith('|'):
                end_pipe = right_part.find('|', 1)
                if end_pipe != -1:
                    edge_label = right_part[1:end_pipe]
                    right_part = right_part[end_pipe+1:].strip()
            
            right_id, right_label, right_type = parse_node_str(right_part)
            if right_id:
                if right_id not in G: G.add_node(right_id, label=right_label, type=right_type)

            if left_id and right_id:
                G.add_edge(left_id, right_id, label=edge_label)
        else:
            node_id, node_label, node_type = parse_node_str(line)
            if node_id:
                if node_id not in G: G.add_node(node_id, label=node_label, type=node_type)

    start_node = None
    for node in G.nodes:
        if G.in_degree(node) == 0:
            start_node = node
            break
    if not start_node and len(G.nodes) > 0:
        start_node = list(G.nodes)[0]
        
    return G, start_node

def parse_node_str(node_str):
    m = re.match(r'(\w+)\s*(\[".*?"\]|\{".*?"\}|\(\[".*?"\]\)|\(\[.*?\]\))?', node_str)
    if not m: return None, None, None
    node_id = m.group(1)
    rest = m.group(2)
    label = node_id
    node_type = 'process'
    if rest:
        if rest.startswith('["'): label = rest[2:-2]; node_type = 'process'
        elif rest.startswith('{"'): label = rest[2:-2]; node_type = 'decision'
        elif rest.startswith('(["'): label = rest[3:-3]; node_type = 'terminal'
        elif rest.startswith('(['): label = rest[2:-2]; node_type = 'terminal'
    return node_id, label, node_type

def build_structure(G, current_node, stop_node, visited):
    blocks = []
    while current_node and current_node != stop_node:
        if current_node in visited:
            blocks.append({'type': 'process', 'label': f'Loop back to {G.nodes[current_node].get("label", current_node)}'})
            break
        
        visited.add(current_node)
        node_data = G.nodes[current_node]
        label = node_data.get('label', current_node)
        successors = list(G.successors(current_node))
        
        if len(successors) == 2:
            merge_node = find_merge_node(G, successors[0], successors[1])
            edge1 = G.get_edge_data(current_node, successors[0])
            label1 = edge1.get('label', '').lower()
            
            if 'ja' in label1 or 'yes' in label1 or 'true' in label1:
                yes_node = successors[0]; no_node = successors[1]
            else:
                yes_node = successors[1]; no_node = successors[0]
            
            yes_block = build_structure(G, yes_node, merge_node, visited.copy())
            no_block = build_structure(G, no_node, merge_node, visited.copy())
            
            blocks.append({
                'type': 'decision',
                'label': label,
                'yes': yes_block,
                'no': no_block
            })
            current_node = merge_node
            
        elif len(successors) == 1:
            blocks.append({'type': 'process', 'label': label})
            current_node = successors[0]
        else:
            blocks.append({'type': 'process', 'label': label})
            current_node = None
            
    return blocks

def find_merge_node(G, node1, node2):
    visited1 = set()
    queue1 = [node1]
    while queue1:
        n = queue1.pop(0)
        if n not in visited1:
            visited1.add(n)
            queue1.extend(G.successors(n))
            if len(visited1) > 100: break
            
    queue2 = [node2]
    visited2 = set()
    while queue2:
        n = queue2.pop(0)
        if n in visited1: return n
        if n not in visited2:
            visited2.add(n)
            queue2.extend(G.successors(n))
            if len(visited2) > 100: break
    return None

def calculate_min_widths(blocks):
    """
    Recursively calculates the minimum width for a list of blocks.
    Annotates each block with 'min_width'.
    Returns the max min_width of the list.
    """
    max_width = MIN_BLOCK_WIDTH
    
    for block in blocks:
        text_width = len(block['label']) * CHAR_WIDTH_AVG + PADDING_X * 2
        
        if block['type'] == 'process':
            block['min_width'] = max(text_width, MIN_BLOCK_WIDTH)
            
        elif block['type'] == 'decision':
            yes_width = calculate_min_widths(block['yes'])
            no_width = calculate_min_widths(block['no'])
            
            # Decision needs to fit its own label too
            decision_label_width = text_width
            
            # The width of a decision block is the sum of its branches
            # But it also needs to be at least wide enough for its header label
            block['min_width'] = max(yes_width + no_width, decision_label_width)
            
            # Store branch widths for proportional rendering
            block['yes_min_width'] = yes_width
            block['no_min_width'] = no_width
            
        max_width = max(max_width, block['min_width'])
        
    return max_width

def calculate_heights(blocks, width):
    """
    Recursively calculates height based on available width.
    Annotates each block with 'height'.
    Returns total height.
    """
    total_h = 0
    for block in blocks:
        # Calculate text wrapping
        # Available width for text
        text_area_width = width - PADDING_X * 2
        text_len = len(block['label']) * CHAR_WIDTH_AVG
        lines = math.ceil(text_len / max(1, text_area_width))
        text_height = lines * LINE_HEIGHT + PADDING_Y * 2
        
        if block['type'] == 'process':
            block['height'] = max(40, text_height)
            total_h += block['height']
            
        elif block['type'] == 'decision':
            # For decision, we split width proportionally based on min_width requirements
            yes_min = block['yes_min_width']
            no_min = block['no_min_width']
            total_min = yes_min + no_min
            
            # Proportional split
            yes_w = width * (yes_min / total_min)
            no_w = width - yes_w
            
            yes_h = calculate_heights(block['yes'], yes_w)
            no_h = calculate_heights(block['no'], no_w)
            
            content_height = max(yes_h, no_h)
            header_height = max(40, text_height + 20) # +20 for diagonals space
            
            block['height'] = header_height + content_height
            block['header_height'] = header_height
            block['content_height'] = content_height
            block['yes_width'] = yes_w
            block['no_width'] = no_w
            
            total_h += block['height']
            
    return total_h

def render_blocks(blocks, x, y, width):
    svg = ""
    current_y = y
    
    for block in blocks:
        if block['type'] == 'process':
            h = block['height']
            svg += f'<rect x="{x}" y="{current_y}" width="{width}" height="{h}" fill="white" stroke="black" stroke-width="1"/>'
            
            # Render text with wrapping
            lines = wrap_text(block['label'], width - PADDING_X * 2)
            text_y = current_y + PADDING_Y + FONT_SIZE/2
            for line in lines:
                svg += f'<text x="{x + 10}" y="{text_y}" font-size="{FONT_SIZE}">{html.escape(line)}</text>'
                text_y += LINE_HEIGHT
                
            current_y += h
            
        elif block['type'] == 'decision':
            header_h = block['header_height']
            content_h = block['content_height']
            yes_w = block['yes_width']
            no_w = block['no_width']
            
            # Header
            svg += f'<rect x="{x}" y="{current_y}" width="{width}" height="{header_h}" fill="#f0f0f0" stroke="black" stroke-width="1"/>'
            svg += f'<line x1="{x}" y1="{current_y}" x2="{x+yes_w}" y2="{current_y+header_h}" stroke="black" stroke-width="1"/>'
            svg += f'<line x1="{x+width}" y1="{current_y}" x2="{x+yes_w}" y2="{current_y+header_h}" stroke="black" stroke-width="1"/>'
            
            # Label
            # User requested logic:
            # 1. Middle of block: x + width/2
            # 2. Intersection point: x + yes_w
            # 3. Position: Average of 1 and 2
            
            block_center_x = x + width / 2
            intersection_x = x + yes_w
            label_x = (block_center_x + intersection_x) / 2
            
            svg += f'<text x="{label_x}" y="{current_y + header_h/2}" text-anchor="middle" font-size="{FONT_SIZE}">{html.escape(block["label"])}</text>'
            
            # True/False
            svg += f'<text x="{x + yes_w/2}" y="{current_y + header_h - 5}" text-anchor="middle" font-size="12">True</text>'
            svg += f'<text x="{x + yes_w + no_w/2}" y="{current_y + header_h - 5}" text-anchor="middle" font-size="12">False</text>'
            
            # Branches
            svg += render_blocks(block['yes'], x, current_y + header_h, yes_w)
            svg += render_blocks(block['no'], x + yes_w, current_y + header_h, no_w)
            
            # Fill empty space
            yes_content_h = sum(b['height'] for b in block['yes'])
            no_content_h = sum(b['height'] for b in block['no'])
            
            if yes_content_h < content_h:
                svg += f'<rect x="{x}" y="{current_y + header_h + yes_content_h}" width="{yes_w}" height="{content_h - yes_content_h}" fill="white" stroke="black" stroke-width="1"/>'
            if no_content_h < content_h:
                svg += f'<rect x="{x + yes_w}" y="{current_y + header_h + no_content_h}" width="{no_w}" height="{content_h - no_content_h}" fill="white" stroke="black" stroke-width="1"/>'
                
            current_y += header_h + content_h

    return svg

def wrap_text(text, max_width):
    """
    Simple word wrap
    """
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    
    for word in words:
        word_len = len(word) * CHAR_WIDTH_AVG
        if current_len + word_len <= max_width:
            current_line.append(word)
            current_len += word_len + CHAR_WIDTH_AVG # Space
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_len = word_len
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines if lines else [text]
