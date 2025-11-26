import ast

class PythonToMermaidConverter(ast.NodeVisitor):
    def __init__(self):
        self.graph_lines = ["graph TD"]
        self.node_counter = 0
        self.stack = []  # Stack to keep track of the previous node to connect from
        self.last_node_id = None

    def generate_id(self):
        self.node_counter += 1
        return f"id{self.node_counter}"

    def add_node(self, label, shape="box"):
        node_id = self.generate_id()
        # Escape quotes in label
        label = label.replace('"', "'")
        
        if shape == "box":
            self.graph_lines.append(f'{node_id}["{label}"]')
        elif shape == "diamond":
            self.graph_lines.append(f'{node_id}{{"{label}"}}')
        elif shape == "rounded":
            self.graph_lines.append(f'{node_id}(["{label}"])')
            
        if self.last_node_id:
            self.graph_lines.append(f"{self.last_node_id} --> {node_id}")
            
        self.last_node_id = node_id
        return node_id

    def convert(self, source_code):
        try:
            tree = ast.parse(source_code)
            self.visit(tree)
            return "\n".join(self.graph_lines)
        except SyntaxError as e:
            return f"graph TD\nError[\"Syntax Error: {e.msg}\"]"

    def visit_FunctionDef(self, node):
        # Treat function definition as a start node for now, or just process body
        # For a simple script, we might just want the body. 
        # But if it's a function, let's show it.
        start_id = self.add_node(f"Start {node.name}", "rounded")
        
        # Save current last_node_id to restore? No, flow continues.
        # Actually, for a function, we might want to isolate it, but let's keep it simple: linear flow.
        
        for stmt in node.body:
            self.visit(stmt)
            
        # We don't explicitly add 'End' unless we want to.
        # Let's add an implicit end if it's the top level? 
        # For now, just let it flow.

    def visit_If(self, node):
        # Condition
        condition_code = ast.get_source_segment(self.source, node.test) if hasattr(self, 'source') else "Condition"
        # Since we don't have source easily without reading file again or passing it, let's try to reconstruct or just use a placeholder if complex.
        # Better: use ast.unparse if available (Python 3.9+) or simple string.
        try:
            condition_text = ast.unparse(node.test)
        except:
            condition_text = "Condition"

        decision_id = self.add_node(f"{condition_text}?", "diamond")
        previous_last_node = self.last_node_id # This is the decision node now
        
        # True branch
        self.last_node_id = decision_id # Start from decision
        # We need to handle the connection manually to add labels
        # Actually add_node adds link from self.last_node_id. 
        # So we need to temporarily disable auto-link or manage it.
        
        # Let's refactor add_node slightly or just manually add edges for control structures.
        
        # Re-implementing logic for If to be more precise
        # Remove the auto-edge added by add_node for the first node of branches?
        # Easier: Manage edges explicitly in control structures.
        
        # Let's stick to a simpler approach:
        # The add_node connects from last_node_id.
        # For IF:
        # 1. Create Decision Node.
        # 2. Visit Body (True path). 
        #    - We need to inject "Yes" label on the first edge.
        # 3. Visit Orelse (False path).
        #    - We need to inject "No" label on the first edge.
        # 4. Merge?
        
        pass # Placeholder, I will implement a more robust version below.

    def generic_visit(self, node):
        # Fallback for unhandled nodes
        super().generic_visit(node)

def convert_python_to_mermaid(source_code):
    converter = SimplePythonToMermaid()
    return converter.convert(source_code)


class SimplePythonToMermaid(ast.NodeVisitor):
    def __init__(self):
        self.lines = ["graph TD"]
        self.count = 0
        self.last_id = None
        self.merge_stack = []

    def new_id(self):
        self.count += 1
        return f"id{self.count}"

    def add_edge(self, from_id, to_id, label=None):
        if not from_id or not to_id: return
        arrow = "-->"
        if label:
            arrow = f"-->|{label}|"
        self.lines.append(f"{from_id} {arrow} {to_id}")

    def add_node(self, label, shape="box"):
        nid = self.new_id()
        label = label.replace('"', "'").strip()
        if shape == "box":
            self.lines.append(f'{nid}["{label}"]')
        elif shape == "diamond":
            self.lines.append(f'{nid}{{"{label}"}}')
        elif shape == "rounded":
            self.lines.append(f'{nid}(["{label}"])')
        return nid

    def convert(self, source):
        self.source = source
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"graph TD\nError[\"Syntax Error: {e.msg}\"]"
            
        # Create a start node
        start_id = self.add_node("Start", "rounded")
        self.last_id = start_id
        
        for node in tree.body:
            self.visit(node)
            
        # Create end node
        end_id = self.add_node("End", "rounded")
        self.add_edge(self.last_id, end_id)
        
        return "\n".join(self.lines)

    def get_source(self, node):
        if hasattr(ast, 'unparse'):
            return ast.unparse(node)
        return "expression"

    def visit_Assign(self, node):
        code = self.get_source(node)
        nid = self.add_node(code)
        self.add_edge(self.last_id, nid)
        self.last_id = nid

    def visit_AugAssign(self, node):
        code = self.get_source(node)
        nid = self.add_node(code)
        self.add_edge(self.last_id, nid)
        self.last_id = nid

    def visit_Expr(self, node):
        code = self.get_source(node)
        nid = self.add_node(code)
        self.add_edge(self.last_id, nid)
        self.last_id = nid
        
    def visit_Return(self, node):
        code = f"return {self.get_source(node.value) if node.value else ''}"
        nid = self.add_node(code)
        self.add_edge(self.last_id, nid)
        self.last_id = nid

    def visit_If(self, node):
        condition = self.get_source(node.test)
        decision_id = self.add_node(f"{condition}?", "diamond")
        self.add_edge(self.last_id, decision_id)
        
        # Save state
        entry_id = decision_id
        
        # True Branch
        self.last_id = entry_id
        # We want the first node in the body to have the "Yes" edge from decision_id
        # But visit() adds nodes and edges.
        # We can't easily intercept the first edge.
        # Strategy: Pass 'parent' and 'edge_label' to visit? No, standard visitor.
        # Strategy: Manually handle the first step of the block?
        
        # Let's try a different approach:
        # We set self.last_id = entry_id.
        # The next visit_X will add an edge from self.last_id.
        # We want that edge to have a label.
        # But visit_X calls add_edge(self.last_id, nid).
        # We can store a "pending_edge_label" in the instance.
        
        self.pending_label = "Yes"
        if node.body:
            for stmt in node.body:
                self.visit(stmt)
        else:
            # Empty body? Pass
            pass
        end_true = self.last_id
        
        # False Branch
        self.last_id = entry_id
        self.pending_label = "No"
        if node.orelse:
            for stmt in node.orelse:
                self.visit(stmt)
        else:
            # If no else, we just draw an edge from decision to merge point?
            # Or we just leave last_id as entry_id (decision)
            pass
        end_false = self.last_id
        
        # Merge
        # We need a merge node to bring them back together
        # But in NSD/Flowchart, we often just continue.
        # Let's create a merge point (invisible or just a connector)
        # Actually, for the next statement, it should connect from BOTH end_true and end_false.
        # This complicates the linear 'last_id'.
        # Solution: 'last_id' can be a list of IDs? Or we insert a dummy merge node.
        # Dummy merge node is safer for Mermaid layout.
        
        merge_id = self.new_id() # Just an ID, maybe a small circle or point?
        # Mermaid doesn't have invisible nodes easily. 
        # Let's just use the next node as the merge target.
        # But we don't know the next node yet.
        # So we MUST have a merge node or handle 'last_id' as a list.
        
        # Let's use a small circle for merge
        # self.lines.append(f'{merge_id}(( ))') 
        # Or just don't output a node, but keep track that the next node connects to multiple.
        
        # Let's try: last_id is a list.
        # But my simple logic assumes single last_id.
        # Let's update add_edge to handle list.
        
        self.last_id = [end_true, end_false]
        self.pending_label = None # Reset

    def visit_While(self, node):
        condition = self.get_source(node.test)
        
        # Loop start (merge point for looping back)
        # We need a node here to jump back to.
        # Let's make the decision the loop start.
        
        decision_id = self.add_node(f"{condition}?", "diamond")
        self.add_edge(self.last_id, decision_id)
        
        # Body
        self.last_id = decision_id
        self.pending_label = "True"
        
        for stmt in node.body:
            self.visit(stmt)
            
        # Loop back
        self.add_edge(self.last_id, decision_id)
        
        # Exit
        self.last_id = decision_id
        self.pending_label = "False"

    def visit_For(self, node):
        target = self.get_source(node.target)
        iter_ = self.get_source(node.iter)
        condition = f"{target} in {iter_}"
        
        decision_id = self.add_node(f"{condition}?", "diamond")
        self.add_edge(self.last_id, decision_id)
        
        self.last_id = decision_id
        self.pending_label = "Next"
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.add_edge(self.last_id, decision_id)
        
        self.last_id = decision_id
        self.pending_label = "Done"

    # Override add_edge to handle list of from_ids and pending labels
    def add_edge(self, from_id, to_id, label=None):
        if not from_id or not to_id: return
        
        # Use pending label if set and no specific label provided
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

