from python_to_mermaid import convert_python_to_mermaid

def test_nested_if():
    code = """
if x > 5:
    if y > 2:
        print("A")
    else:
        print("B")
else:
    print("C")
print("Done")
"""
    mermaid = convert_python_to_mermaid(code)
    print("--- Nested If ---")
    print(mermaid)

if __name__ == "__main__":
    test_nested_if()
