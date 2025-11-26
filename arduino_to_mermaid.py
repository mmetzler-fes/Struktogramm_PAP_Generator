import re

class ArduinoToMermaidConverter:
    def __init__(self):
        self.lines = ["graph TD"]
        self.node_counter = 0
        self.last_id = None
        self.loop_start_id = None

    def new_id(self):
        self.node_counter += 1
        return f"id{self.node_counter}"

    def add_node(self, label, shape="box"):
        nid = self.new_id()
        # Escape quotes
        label = label.replace('"', "'").strip()
        if not label: label = "Statement"
        
        if shape == "box":
            self.lines.append(f'{nid}["{label}"]')
        elif shape == "diamond":
            self.lines.append(f'{nid}{{"{label}"}}')
        elif shape == "rounded":
            self.lines.append(f'{nid}(["{label}"])')
        elif shape == "circle":
             self.lines.append(f'{nid}(({label}))')
            
        return nid

    def add_edge(self, from_id, to_id, label=None):
        if not from_id or not to_id: return
        
        if isinstance(from_id, list):
            for fid in from_id:
                self.add_edge(fid, to_id, label)
            return

        arrow = "-->"
        if label:
            arrow = f"-->|{label}|"
        self.lines.append(f"{from_id} {arrow} {to_id}")

    def convert(self, source_code):
        # Remove comments
        source_code = re.sub(r'//.*', '', source_code)
        source_code = re.sub(r'/\*.*?\*/', '', source_code, flags=re.DOTALL)
        
        self.source = source_code
        
        # Find setup and loop
        setup_match = re.search(r'void\s+setup\s*\(\s*\)\s*\{', source_code)
        loop_match = re.search(r'void\s+loop\s*\(\s*\)\s*\{', source_code)
        
        start_node = self.add_node("Start", "rounded")
        self.last_id = start_node
        
        if setup_match:
            setup_start = setup_match.end()
            setup_end = self.find_matching_brace(source_code, setup_start - 1)
            setup_body = source_code[setup_start:setup_end]
            self.parse_block(setup_body)
            
        if loop_match:
            loop_start = loop_match.end()
            loop_end = self.find_matching_brace(source_code, loop_start - 1)
            loop_body = source_code[loop_start:loop_end]
            
            # Loop entry point
            loop_entry = self.add_node("Loop Start", "diamond")
            self.add_edge(self.last_id, loop_entry)
            self.last_id = loop_entry
            
            # Pass loop_entry as the current_id for the block, and indicate it's a loop body
            self.parse_block(loop_body, current_id=loop_entry, is_loop_body=True)
            
            # Connect back to loop start if the loop body wasn't terminal
            if self.last_id: # If last_id is None, it means the loop body was terminal
                self.add_edge(self.last_id, loop_entry)
            
            # Technically Arduino loop never ends, but for visualization we might show it
            # But here we just loop back.
            
        return "\n".join(self.lines)

    def find_matching_brace(self, text, start_index):
        brace_count = 0
        for i in range(start_index, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
        return len(text)

    def extract_block(self, text):
        """Helper to extract content within the first { } block."""
        brace_count = 0
        start = -1
        for i, char in enumerate(text):
            if char == '{':
                if start == -1:
                    start = i + 1
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start != -1:
                    return text[start:i]
        return "" # Should not happen for valid code

    def parse_block(self, content, current_id=None, is_loop_body=False):
        # Simple recursive descent parser for block content
        # We look for: if, while, for, and statements ending in ;
        
        if current_id is None:
            current_id = self.last_id

        i = 0
        while i < len(content):
            # Skip whitespace
            while i < len(content) and content[i].isspace():
                i += 1
            if i >= len(content): break
    def parse_block(self, block_content, current_id=None, is_loop_body=False):
        # Split into statements (basic implementation)
        
        # Initialize current_ids
        if current_id is None:
            current_ids = [self.last_id] if self.last_id else []
        elif isinstance(current_id, list):
            current_ids = current_id
        else:
            current_ids = [current_id]
            
        # Remove None values
        current_ids = [pid for pid in current_ids if pid is not None]
        
        remaining = block_content.strip()
        
        while remaining:
            # Check for control structures
            if remaining.startswith('if'):
                # Handle If
                match = re.search(r'if\s*\(.*\)\s*\{', remaining)
                if match:
                    if_body_start_idx = match.end() - 1
                    if_body_end_idx = self.find_matching_brace(remaining, if_body_start_idx)
                    
                    full_if_part_len = if_body_end_idx + 1
                    
                    # Check for else
                    temp_remaining = remaining[full_if_part_len:].strip()
                    full_statement_len = full_if_part_len
                    
                    if temp_remaining.startswith('else'):
                         # Extract else part
                         else_match = re.search(r'else\s*(\s*if\s*\(.*?\)\s*)?\{', temp_remaining)
                         if else_match:
                             else_brace_rel_idx = else_match.end() - 1
                             else_brace_abs_idx = full_statement_len + (len(remaining[full_statement_len:]) - len(temp_remaining)) + else_brace_rel_idx
                             
                             else_body_end_idx = self.find_matching_brace(remaining, else_brace_abs_idx)
                             full_statement_len = else_body_end_idx + 1
                    
                    exits = self.parse_if(remaining[:full_statement_len], current_ids)
                    
                    current_ids = exits if isinstance(exits, list) else ([exits] if exits else [])
                    remaining = remaining[full_statement_len:].strip()
                    continue

            elif remaining.startswith('while'):
                 # Handle While
                 match = re.search(r'while\s*\(.*\)\s*\{', remaining)
                 if match:
                     body_start_idx = match.end() - 1
                     body_end_idx = self.find_matching_brace(remaining, body_start_idx)
                     full_statement_len = body_end_idx + 1
                     
                     loop_exit = self.parse_while(remaining[:full_statement_len], current_ids)
                     
                     current_ids = [loop_exit] if loop_exit else []
                     remaining = remaining[full_statement_len:].strip()
                     continue

            elif remaining.startswith('for'):
                 # Handle For
                 match = re.search(r'for\s*\(.*\)\s*\{', remaining)
                 if match:
                     body_start_idx = match.end() - 1
                     body_end_idx = self.find_matching_brace(remaining, body_start_idx)
                     full_statement_len = body_end_idx + 1
                     
                     loop_exit = self.parse_for(remaining[:full_statement_len], current_ids)
                     
                     current_ids = [loop_exit] if loop_exit else []
                     remaining = remaining[full_statement_len:].strip()
                     continue
            
            # Basic statement (ends with ;)
            semicolon = remaining.find(';')
            brace = remaining.find('{')
            
            if semicolon != -1 and (brace == -1 or semicolon < brace):
                statement = remaining[:semicolon].strip()
                remaining = remaining[semicolon+1:].strip()
                
                if not statement: continue
                
                # Create node
                node_id = self.add_node(statement)
                
                # Connect all parents to this node
                self.add_edge(current_ids, node_id)
                
                current_ids = [node_id]
            else:
                # Unknown or complex structure
                break
                
        # Return the last node ID(s) of this block
        # If current_ids is empty, it means the block is terminal (e.g. infinite loop)
        if not current_ids: 
            self.last_id = None
            return None
            
        final_id = current_ids[0] if len(current_ids) == 1 else current_ids
        self.last_id = final_id
        return final_id

    def parse_if(self, content, current_id):
        # Match if (condition) {
        
        open_paren = content.find('(')
        if open_paren == -1: return current_id
        
        close_paren = self.find_matching_paren(content, open_paren)
        condition = content[open_paren+1:close_paren].strip()
        
        brace_start = content.find('{', close_paren)
        if brace_start == -1: return current_id
        
        brace_end = self.find_matching_brace(content, brace_start)
        true_body = content[brace_start+1:brace_end]
        
        # Create decision node
        decision_id = self.add_node(f"{condition}?", "diamond")
        self.add_edge(current_id, decision_id)
        
        # True Branch
        self.pending_label = "Yes"
        end_true = self.parse_block(true_body, decision_id)
        self.pending_label = None
        
        # Check for else
        remaining = content[brace_end+1:].strip()
        end_false = None
        
        if remaining.startswith('else'):
            else_brace_start = remaining.find('{')
            if else_brace_start != -1:
                else_brace_end = self.find_matching_brace(remaining, else_brace_start)
                false_body = remaining[else_brace_start+1:else_brace_end]
                
                self.pending_label = "No"
                end_false = self.parse_block(false_body, decision_id)
                self.pending_label = None
            else:
                pass
        
        # Collect exits
        exits = []
        if end_true:
            if isinstance(end_true, list): exits.extend(end_true)
            else: exits.append(end_true)
            
        if end_false:
            if isinstance(end_false, list): exits.extend(end_false)
            else: exits.append(end_false)
        elif not remaining.startswith('else'):
             # If no else, decision_id is an exit (No branch)
             # We label it "No"
             exits.append((decision_id, "No"))
             
        return exits

    def parse_while(self, content, current_id):
        open_paren = content.find('(')
        close_paren = self.find_matching_paren(content, open_paren)
        condition = content[open_paren+1:close_paren].strip()
        
        # Check for infinite loop
        is_infinite = condition == 'true' or condition == '1'
        
        brace_start = content.find('{', close_paren)
        brace_end = self.find_matching_brace(content, brace_start)
        body = content[brace_start+1:brace_end]
        
        loop_id = self.add_node(f"while({condition})", "diamond" if not is_infinite else "diamond")
        # If infinite, maybe use a different shape or label?
        # User wants "while(true)" in a diamond.
        
        self.add_edge(current_id, loop_id)
        
        self.pending_label = "True" if not is_infinite else None # Infinite loop body is just the path
        # Actually, for while(true), we usually don't label the entry to body as "True" if it's the only path.
        # But consistency is good.
        
        end_body = self.parse_block(body, loop_id, is_loop_body=True)
        self.pending_label = None
        
        # Connect back
        self.add_edge(end_body, loop_id)
        
        if is_infinite:
            return None # No exit
        else:
            return loop_id # Exit is the loop header (False branch)

    def parse_for(self, content, current_id):
        open_paren = content.find('(')
        close_paren = self.find_matching_paren(content, open_paren)
        header = content[open_paren+1:close_paren].strip()
        
        brace_start = content.find('{', close_paren)
        brace_end = self.find_matching_brace(content, brace_start)
        body = content[brace_start+1:brace_end]
        
        loop_id = self.add_node(f"For {header}", "diamond")
        self.add_edge(current_id, loop_id)
        
        self.pending_label = "Next"
        end_body = self.parse_block(body, loop_id, is_loop_body=True)
        self.pending_label = None
        
        self.add_edge(end_body, loop_id)
        
        return loop_id # Exit is loop header (Done)

    def find_matching_paren(self, text, start_index):
        count = 0
        for i in range(start_index, len(text)):
            if text[i] == '(':
                count += 1
            elif text[i] == ')':
                count -= 1
                if count == 0:
                    return i
        return len(text)
        
    # Override add_edge to handle pending label
    def add_edge(self, from_id, to_id, label=None):
        if not from_id or not to_id: return
        
        if not label and hasattr(self, 'pending_label') and self.pending_label:
            label = self.pending_label
            self.pending_label = None
            
        if isinstance(from_id, list):
            for item in from_id:
                if isinstance(item, tuple):
                    fid, lbl = item
                    self.add_edge(fid, to_id, lbl or label)
                else:
                    self.add_edge(item, to_id, label)
            return

        arrow = "-->"
        if label:
            arrow = f"-->|{label}|"
        self.lines.append(f"{from_id} {arrow} {to_id}")

def convert_arduino_to_mermaid(source_code):
    converter = ArduinoToMermaidConverter()
    return converter.convert(source_code)
