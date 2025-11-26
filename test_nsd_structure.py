from converter import convert_mermaid_to_nsd

def test_loop_rendering():
    mermaid_code = """
graph TD
A[Start] --> B{x < 10?}
B -->|Yes| C[x++]
C --> B
B -->|No| D[End]
"""
    svg = convert_mermaid_to_nsd(mermaid_code)
    print("--- Loop SVG ---")
    print(svg) 
    
    # Check for loop specific elements
    # We expect a side bar with width 30 (LOOP_INDENT)
    if 'width="30"' in svg:
        print("SUCCESS: Found loop side bar (width=30)")
    else:
        print("FAILURE: Loop side bar not found")
        
    # Check for loop label
    if 'x &lt; 10?' in svg:
        print("SUCCESS: Found loop condition")
    else:
        print("FAILURE: Loop condition not found")

    # Check that body is rendered
    if 'x++' in svg:
        print("SUCCESS: Found loop body")
    else:
        print("FAILURE: Loop body not found")

if __name__ == "__main__":
    test_loop_rendering()
