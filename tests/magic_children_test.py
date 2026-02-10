from dataclasses import dataclass
import pytest

@dataclass(slots=True)
class SlottedComponent:
    name: str
    # No children declared

def test_magic_injection_on_slots():
    comp = SlottedComponent(name="test")
    
    # This simulates what the library would have to do to support 
    # "undeclared children" on a class component
    with pytest.raises(AttributeError):
        comp.children = ("child1",)
        
@dataclass
class StandardComponent:
    name: str
    # No children declared

def test_magic_injection_on_standard():
    comp = StandardComponent(name="test")
    # This works but static analysis tools won't know about 'children'
    comp.children = ("child1",)
    assert comp.children == ("child1",)

if __name__ == "__main__":
    try:
        test_magic_injection_on_slots()
        print("Slots prevented injection (Expected)")
    except Exception as e:
        print(f"Slots test failed: {e}")
        
    test_magic_injection_on_standard()
    print("Standard injection worked")
