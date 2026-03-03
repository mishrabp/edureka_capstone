
import os
import sys

# Ensure the project root is in the path
sys.path.append(os.getcwd())

from app.core.agent import _build_graph

def generate_graph_image():
    try:
        app = _build_graph()
        # Use mermaid to generate the PNG bytes
        png_bytes = app.get_graph().draw_mermaid_png()
        
        output_path = "docs/images/langgraph_generated.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        
        print(f"Graph image successfully saved to {output_path}")
    except Exception as e:
        print(f"Error generating graph image: {e}")
        # Fallback for environments without pygraphviz/mermaid: 
        # We can try draw_ascii if needed, but the user specifically asked for 'image'
        sys.exit(1)

if __name__ == "__main__":
    generate_graph_image()
