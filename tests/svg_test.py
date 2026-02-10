from tdom import html

def test_svg_case_sensitivity():
    # SVG attributes like viewBox are case-sensitive
    node = html(t'<svg viewBox="0 0 100 100"></svg>')
    print(f"Node: {node}")
    # We expect viewBox, not viewbox
    if 'viewBox' in str(node):
        print("Case preserved")
    else:
        print("Case LOST")

if __name__ == "__main__":
    test_svg_case_sensitivity()
