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
            
            self.parse_block(loop_body)
            
            # Connect back to loop start
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

    def parse_block(self, content):
        # Simple recursive descent parser for block content
        # We look for: if, while, for, and statements ending in ;
        
        i = 0
        while i < len(content):
            # Skip whitespace
            while i < len(content) and content[i].isspace():
                i += 1
            if i >= len(content): break
            
            # Check for control structures
            rest = content[i:]
            
            if rest.startswith('if'):
                i = self.parse_if(content, i)
            elif rest.startswith('while'):
                i = self.parse_while(content, i)
            elif rest.startswith('for'):
                i = self.parse_for(content, i)
            else:
                # Statement
                # Find next ; or } or { (if block starts without keyword? unlikely in valid C code we care about)
                # Actually, we just look for ;
                semi = content.find(';', i)
                if semi != -1:
                    stmt = content[i:semi].strip()
                    if stmt:
                        nid = self.add_node(stmt)
                        self.add_edge(self.last_id, nid)
                        self.last_id = nid
                    i = semi + 1
                else:
                    # End of block or error
                    break

    def parse_if(self, content, start_index):
        # Match if (condition) {
        # We need to find the condition and the body
        
        # Find (
        open_paren = content.find('(', start_index)
        if open_paren == -1: return len(content)
        
        # Find matching )
        close_paren = self.find_matching_paren(content, open_paren)
        condition = content[open_paren+1:close_paren].strip()
        
        # Find {
        brace_start = content.find('{', close_paren)
        if brace_start == -1: return len(content) # Single line if not supported for simplicity
        
        brace_end = self.find_matching_brace(content, brace_start)
        true_body = content[brace_start+1:brace_end]
        
        # Create decision node
        decision_id = self.add_node(f"{condition}?", "diamond")
        self.add_edge(self.last_id, decision_id)
        
        entry_id = decision_id
        
        # True Branch
        self.last_id = entry_id
        # Add edge with label Yes manually for first node?
        # We can use a temporary "pending label" mechanism like in python converter
        # Or just add a dummy node if needed.
        # Let's use pending label approach.
        self.pending_label = "Yes"
        
        self.parse_block(true_body)
        end_true = self.last_id
        
        # Check for else
        next_idx = brace_end + 1
        while next_idx < len(content) and content[next_idx].isspace():
            next_idx += 1
            
        end_false = entry_id # Default if no else
        
        if content[next_idx:].startswith('else'):
            # Handle else
            else_start = next_idx + 4
            # Check for {
            else_brace_start = content.find('{', else_start)
            if else_brace_start != -1:
                else_brace_end = self.find_matching_brace(content, else_brace_start)
                false_body = content[else_brace_start+1:else_brace_end]
                
                self.last_id = entry_id
                self.pending_label = "No"
                self.parse_block(false_body)
                end_false = self.last_id
                
                next_idx = else_brace_end + 1
            else:
                # else if? or single line else?
                # For now assume block
                pass
        else:
            # No else, draw No edge to merge point?
            # Or just leave end_false as entry_id
            pass
            
        # Merge
        self.last_id = [end_true, end_false]
        self.pending_label = None
        
        return next_idx

    def parse_while(self, content, start_index):
        open_paren = content.find('(', start_index)
        close_paren = self.find_matching_paren(content, open_paren)
        condition = content[open_paren+1:close_paren].strip()
        
        brace_start = content.find('{', close_paren)
        brace_end = self.find_matching_brace(content, brace_start)
        body = content[brace_start+1:brace_end]
        
        decision_id = self.add_node(f"{condition}?", "diamond")
        self.add_edge(self.last_id, decision_id)
        
        self.last_id = decision_id
        self.pending_label = "True"
        
        self.parse_block(body)
        
        self.add_edge(self.last_id, decision_id)
        
        self.last_id = decision_id
        self.pending_label = "False"
        
        return brace_end + 1

    def parse_for(self, content, start_index):
        open_paren = content.find('(', start_index)
        close_paren = self.find_matching_paren(content, open_paren)
        header = content[open_paren+1:close_paren].strip()
        
        brace_start = content.find('{', close_paren)
        brace_end = self.find_matching_brace(content, brace_start)
        body = content[brace_start+1:brace_end]
        
        decision_id = self.add_node(f"For {header}", "diamond")
        self.add_edge(self.last_id, decision_id)
        
        self.last_id = decision_id
        self.pending_label = "Next"
        
        self.parse_block(body)
        
        self.add_edge(self.last_id, decision_id)
        
        self.last_id = decision_id
        self.pending_label = "Done"
        
        return brace_end + 1

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
            for fid in from_id:
                self.add_edge(fid, to_id, label)
            return

        arrow = "-->"
        if label:
            arrow = f"-->|{label}|"
        self.lines.append(f"{from_id} {arrow} {to_id}")

def convert_arduino_to_mermaid(source_code):
    converter = ArduinoToMermaidConverter()
    return converter.convert(source_code)
