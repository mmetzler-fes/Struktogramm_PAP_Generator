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
LOOP_INDENT = 30  # Width of the side bar for loops

def convert_mermaid_to_nsd(mermaid_content):
    graph, start_node = parse_mermaid(mermaid_content)
    if not start_node:
        return '<svg><text>Error: No start node found</text></svg>'
        
    structured_tree = build_structure(graph, start_node, None, set())
    
    # 1. Calculate Minimum Widths
    total_min_width = calculate_min_widths(structured_tree)
    
    # Ensure a reasonable total width
    width = max(800, total_min_width)
    
    # 2. Calculate Heights
    total_height = calculate_heights(structured_tree, width)
    
    svg_content = render_blocks(structured_tree, 0, 0, width)
    
    return f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">{svg_content}</svg>'

def parse_mermaid(content):
    G = nx.DiGraph()
    lines = content.split('\n')
    
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
    # Match id followed by optional brackets containing label
    # We use non-greedy match .*? inside brackets
    m = re.match(r'(\w+)\s*(\[.*?\]|\{.*?\}|\(\[.*?\]\)|\(\(.*?\)|\))?', node_str)
    if not m: return None, None, None
    node_id = m.group(1)
    rest = m.group(2)
    label = node_id
    node_type = 'process'
    
    if rest:
        content = ""
        if rest.startswith('["'): 
            content = rest[2:-2]
            node_type = 'process'
        elif rest.startswith('['): 
            content = rest[1:-1]
            node_type = 'process'
        elif rest.startswith('{"'): 
            content = rest[2:-2]
            node_type = 'decision'
        elif rest.startswith('{'): 
            content = rest[1:-1]
            node_type = 'decision'
        elif rest.startswith('(["'): 
            content = rest[3:-3]
            node_type = 'terminal'
        elif rest.startswith('(['): 
            content = rest[2:-2]
            node_type = 'terminal'
        elif rest.startswith('(("'): 
            content = rest[3:-3]
            node_type = 'terminal'
        elif rest.startswith('(('): 
            content = rest[2:-2]
            node_type = 'terminal'
            
        # Strip quotes if they were not stripped by specific checks above (e.g. mixed case)
        # Actually the above covers ["..."] and [...].
        # But if we have [ "Label" ], the space might be an issue?
        # Let's just strip surrounding quotes if present.
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        
        label = content
            
    return node_id, label, node_type

def build_structure(G, current_node, stop_node, visited):
    blocks = []
    # visited set in this context is for the current recursion path to detect immediate loops if needed,
    # but we rely on graph topology for loop detection now.
    # Actually, we still need visited to avoid infinite recursion if we don't detect the loop correctly.
    
    while current_node and current_node != stop_node:
        if current_node in visited:
            break
        visited.add(current_node)
        
        # Get node info
        node_data = G.nodes[current_node]
        label = node_data.get('label', '').replace('"', '')
        successors = list(G.successors(current_node))
        
        if len(successors) == 2:
            # Check for Loop (Head-Controlled)
            # A loop header has one branch that leads back to itself, and one that doesn't (exit).
            # BUT: If both lead back (nested if in loop), it's not a loop header for *this* loop, but an inner structure.
            # We assume structured programming: Loop Header dominates the body.
            
            s0 = successors[0]
            s1 = successors[1]
            
            # Check reachability back to current_node
            # We must be careful: s0 -> ... -> current_node
            # If s0 is stop_node, it cannot lead back within the current scope.
            leads_back_0 = False if (stop_node and s0 == stop_node) else has_path_excluding(G, s0, current_node, stop_node)
            leads_back_1 = False if (stop_node and s1 == stop_node) else has_path_excluding(G, s1, current_node, stop_node)
            
            if leads_back_0 and not leads_back_1:
                # s0 is body, s1 is exit
                # Loop Header is current_node.
                # Stop node for body is current_node.
                loop_body_start = s0
                exit_node = s1
                is_loop = True
            elif leads_back_1 and not leads_back_0:
                # s1 is body, s0 is exit
                loop_body_start = s1
                exit_node = s0
                is_loop = True
            else:
                is_loop = False
                
            if is_loop:
                # It is a loop!
                # Build body. Stop node is current_node (the header).
                # We need to pass a copy of visited? Yes.
                body_blocks = build_structure(G, loop_body_start, current_node, visited.copy())
                
                blocks.append({
                    'type': 'loop',
                    'label': label,
                    'body': body_blocks
                })
                current_node = exit_node
                continue

            # Standard Decision
            merge_node = find_merge_node(G, successors[0], successors[1], stop_node)
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
            # Check for Loop (Infinite or Foot-Controlled)
            # If the single successor leads back to current_node, it's a loop.
            s0 = successors[0]
            
            # CRITICAL: If s0 is the stop_node, this is just the back-edge of the parent loop.
            if stop_node and s0 == stop_node:
                blocks.append({'type': 'process', 'label': label})
                current_node = s0
            elif has_path_excluding(G, s0, current_node, stop_node):
                # It is a loop!
                body_blocks = build_structure(G, s0, current_node, visited.copy())
                
                blocks.append({
                    'type': 'loop',
                    'label': label,
                    'body': body_blocks
                })
                current_node = None 
            else:
                blocks.append({'type': 'process', 'label': label})
                current_node = successors[0]
        else:
            blocks.append({'type': 'process', 'label': label})
            current_node = None
            
    return blocks

def has_path_excluding(G, source, target, exclude_node):
    if source == target: return True
    if exclude_node is None:
        return nx.has_path(G, source, target)
        
    # BFS to find path without visiting exclude_node
    visited = {source, exclude_node}
    queue = [source]
    
    while queue:
        n = queue.pop(0)
        if n == target: return True
        
        for succ in G.successors(n):
            if succ not in visited:
                visited.add(succ)
                queue.append(succ)
    return False

def find_merge_node(G, node1, node2, stop_node=None):
    visited1 = set()
    queue1 = [node1]
    while queue1:
        n = queue1.pop(0)
        if n == stop_node: continue 
        if n not in visited1:
            visited1.add(n)
            queue1.extend(G.successors(n))
            if len(visited1) > 100: break
            
    queue2 = [node2]
    visited2 = set()
    while queue2:
        n = queue2.pop(0)
        if n == stop_node: continue
        if n in visited1: 
            return n
        if n not in visited2:
            visited2.add(n)
            queue2.extend(G.successors(n))
            if len(visited2) > 100: break
    return None

def calculate_min_widths(blocks):
    max_width = MIN_BLOCK_WIDTH
    
    for block in blocks:
        text_width = len(block['label']) * CHAR_WIDTH_AVG + PADDING_X * 2
        
        if block['type'] == 'process':
            block['min_width'] = max(text_width, MIN_BLOCK_WIDTH)
            
        elif block['type'] == 'decision':
            yes_width = calculate_min_widths(block['yes'])
            no_width = calculate_min_widths(block['no'])
            decision_label_width = text_width
            block['min_width'] = max(yes_width + no_width, decision_label_width)
            block['yes_min_width'] = yes_width
            block['no_min_width'] = no_width
            
        elif block['type'] == 'loop':
            body_width = calculate_min_widths(block['body'])
            # Loop needs width for body + indent
            # And width for label
            block['min_width'] = max(body_width + LOOP_INDENT, text_width)
            block['body_min_width'] = body_width

        max_width = max(max_width, block['min_width'])
        
    return max_width

def calculate_heights(blocks, width):
    total_h = 0
    for block in blocks:
        text_area_width = width - PADDING_X * 2
        text_len = len(block['label']) * CHAR_WIDTH_AVG
        lines = math.ceil(text_len / max(1, text_area_width))
        text_height = lines * LINE_HEIGHT + PADDING_Y * 2
        
        if block['type'] == 'process':
            block['height'] = max(40, text_height)
            total_h += block['height']
            
        elif block['type'] == 'decision':
            yes_min = block['yes_min_width']
            no_min = block['no_min_width']
            total_min = yes_min + no_min
            
            yes_w = width * (yes_min / total_min)
            no_w = width - yes_w
            
            yes_h = calculate_heights(block['yes'], yes_w)
            no_h = calculate_heights(block['no'], no_w)
            
            content_height = max(yes_h, no_h)
            header_height = max(40, text_height + 20)
            
            block['height'] = header_height + content_height
            block['header_height'] = header_height
            block['content_height'] = content_height
            block['yes_width'] = yes_w
            block['no_width'] = no_w
            
            total_h += block['height']
            
        elif block['type'] == 'loop':
            # Loop layout:
            # Header bar (text_height)
            # Body (indented)
            
            header_height = max(30, text_height)
            
            # Body width is width - LOOP_INDENT
            body_w = width - LOOP_INDENT
            body_h = calculate_heights(block['body'], body_w)
            
            block['height'] = header_height + body_h
            block['header_height'] = header_height
            block['body_height'] = body_h
            block['body_width'] = body_w
            
            total_h += block['height']
            
    return total_h

def render_blocks(blocks, x, y, width):
    svg = ""
    current_y = y
    
    for block in blocks:
        if block['type'] == 'process':
            h = block['height']
            svg += f'<rect x="{x}" y="{current_y}" width="{width}" height="{h}" fill="white" stroke="black" stroke-width="1"/>'
            
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
            
            svg += f'<rect x="{x}" y="{current_y}" width="{width}" height="{header_h}" fill="#f0f0f0" stroke="black" stroke-width="1"/>'
            svg += f'<line x1="{x}" y1="{current_y}" x2="{x+yes_w}" y2="{current_y+header_h}" stroke="black" stroke-width="1"/>'
            svg += f'<line x1="{x+width}" y1="{current_y}" x2="{x+yes_w}" y2="{current_y+header_h}" stroke="black" stroke-width="1"/>'
            
            block_center_x = x + width / 2
            intersection_x = x + yes_w
            label_x = (block_center_x + intersection_x) / 2
            
            svg += f'<text x="{label_x}" y="{current_y + header_h/2}" text-anchor="middle" font-size="{FONT_SIZE}">{html.escape(block["label"])}</text>'
            
            svg += f'<text x="{x + yes_w/2}" y="{current_y + header_h - 5}" text-anchor="middle" font-size="12">True</text>'
            svg += f'<text x="{x + yes_w + no_w/2}" y="{current_y + header_h - 5}" text-anchor="middle" font-size="12">False</text>'
            
            svg += render_blocks(block['yes'], x, current_y + header_h, yes_w)
            svg += render_blocks(block['no'], x + yes_w, current_y + header_h, no_w)
            
            yes_content_h = sum(b['height'] for b in block['yes'])
            no_content_h = sum(b['height'] for b in block['no'])
            
            if yes_content_h < content_h:
                svg += f'<rect x="{x}" y="{current_y + header_h + yes_content_h}" width="{yes_w}" height="{content_h - yes_content_h}" fill="white" stroke="black" stroke-width="1"/>'
            if no_content_h < content_h:
                svg += f'<rect x="{x + yes_w}" y="{current_y + header_h + no_content_h}" width="{no_w}" height="{content_h - no_content_h}" fill="white" stroke="black" stroke-width="1"/>'
                
            current_y += header_h + content_h

        elif block['type'] == 'loop':
            h = block['height']
            header_h = block['header_height']
            body_h = block['body_height']
            body_w = block['body_width']
            
            # Draw L-shape container using a path to avoid line between header and side bar
            # Points:
            # 1. Top-Left (x, y)
            # 2. Top-Right (x + width, y)
            # 3. Header-Bottom-Right (x + width, y + header_h)
            # 4. Inner-Corner (x + LOOP_INDENT, y + header_h)
            # 5. Bottom-Right of Side Bar (x + LOOP_INDENT, y + h)
            # 6. Bottom-Left (x, y + h)
            # Close path
            
            p1 = f"{x},{current_y}"
            p2 = f"{x+width},{current_y}"
            p3 = f"{x+width},{current_y+header_h}"
            p4 = f"{x+LOOP_INDENT},{current_y+header_h}"
            p5 = f"{x+LOOP_INDENT},{current_y+h}"
            p6 = f"{x},{current_y+h}"
            
            path_d = f"M {p1} L {p2} L {p3} L {p4} L {p5} L {p6} Z"
            
            svg += f'<path d="{path_d}" fill="#e0e0e0" stroke="black" stroke-width="1"/>'
            svg += f'<text x="{x + 10}" y="{current_y + header_h/2 + 5}" font-size="{FONT_SIZE}">{html.escape(block["label"])}</text>'
            
            # Body area (white background for body blocks)
            # The blocks will draw themselves.
            
            svg += render_blocks(block['body'], x + LOOP_INDENT, current_y + header_h, body_w)
            
            current_y += h

    return svg

def wrap_text(text, max_width):
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    
    for word in words:
        word_len = len(word) * CHAR_WIDTH_AVG
        if current_len + word_len <= max_width:
            current_line.append(word)
            current_len += word_len + CHAR_WIDTH_AVG 
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_len = word_len
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines if lines else [text]
