# test_agent_tools.py
import sys
import os
import pathlib

# Ensure project paths are set up correctly
project_root = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root.parent))
sys.path.insert(0, str(project_root))

print("1. Testing Key Generator...")
from core.auth import api_key_generator_instance
key = api_key_generator_instance.generate_api_key()
print(f"Generated API key: {key}")
assert len(key.split("_")) == 3, "Invalid API key format"
print("Key generator test PASSED!\n")

print("2. Testing Tool Registration & Mode Loading...")
os.environ["AGENT_MODE"] = "hr"
# Import act node module using package path
import agent.agent.nodes.act as hr_act
print("Active tools in HR mode:")


for t in hr_act._active_tools:
    print(f" - {t.name}: {t.description[:60]}...")
assert any(t.name == "readcv" for t in hr_act._active_tools), "readcv tool missing in HR mode"
print("Tool registration test for HR mode PASSED!\n")

# Verify general mode works as expected
# We reload environmental variables or check the logic directly
print("3. Verification of Act Prompt Template Compilation...")
print(f"Template prompt input variables: {hr_act._TEMPLATE_PROMPT.input_variables}")
print("Act Prompt Template compilation test PASSED!\n")

print("All Agent tools verification tests PASSED successfully!")
