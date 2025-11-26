from arduino_to_mermaid import convert_arduino_to_mermaid

def test_blink():
    code = """
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);   // turn the LED on (HIGH is the voltage level)
  delay(1000);                       // wait for a second
  digitalWrite(LED_BUILTIN, LOW);    // turn the LED off by making the voltage LOW
  delay(1000);                       // wait for a second
}
"""
    mermaid = convert_arduino_to_mermaid(code)
    print("--- Blink ---")
    print(mermaid)
    assert "Start" in mermaid
    assert "Loop Start" in mermaid
    assert "pinMode(LED_BUILTIN, OUTPUT)" in mermaid
    assert "digitalWrite(LED_BUILTIN, HIGH)" in mermaid

def test_control_structures():
    code = """
void loop() {
  if (x > 5) {
    doSomething();
  } else {
    doOther();
  }
  
  while (y < 10) {
    y++;
  }
  
  for (int i=0; i<10; i++) {
    print(i);
  }
}
"""
    mermaid = convert_arduino_to_mermaid(code)
    print("\n--- Control Structures ---")
    print(mermaid)
    assert "x > 5?" in mermaid
    assert "y < 10?" in mermaid
    assert "For int i=0; i<10; i++" in mermaid

if __name__ == "__main__":
    test_blink()
    test_control_structures()
    print("\nAll tests passed!")
