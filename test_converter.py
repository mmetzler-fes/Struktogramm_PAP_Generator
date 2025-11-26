from python_to_mermaid import convert_python_to_mermaid

def test_simple_function():
    code = """
def hello():
    print("Hello")
    return True
"""
    mermaid = convert_python_to_mermaid(code)
    print("--- Simple Function ---")
    print(mermaid)
    assert "graph TD" in mermaid
    assert "Start" in mermaid
    assert "End" in mermaid

def test_if_else():
    code = """
if x > 5:
    print("Big")
else:
    print("Small")
"""
    mermaid = convert_python_to_mermaid(code)
    print("\n--- If Else ---")
    print(mermaid)
    assert "x > 5?" in mermaid
    assert "-->|Yes|" in mermaid
    assert "-->|No|" in mermaid

def test_loop():
    code = """
while x < 10:
    x += 1
"""
    mermaid = convert_python_to_mermaid(code)
    print("\n--- Loop ---")
    print(mermaid)
    assert "x < 10?" in mermaid
    assert "-->|True|" in mermaid
    assert "-->|False|" in mermaid

if __name__ == "__main__":
    test_simple_function()
    test_if_else()
    test_loop()
    print("\nAll tests passed!")
