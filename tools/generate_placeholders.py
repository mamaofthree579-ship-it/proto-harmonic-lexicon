"""
generate_placeholders.py
--------------------------------------
Generates simple SVG placeholders for each motif in motifs_expanded.csv
to populate the data/images/ directory.
Each placeholder encodes motif region, harmonic ratio, and frequency cluster
as simple geometry & color so Streamlit can render symbolic previews.
"""

import os
import math
import pandas as pd
from pathlib import Path

# Input/output paths
CSV_PATH = Path("data/motifs_expanded.csv")
IMG_DIR = Path("data/images")
IMG_DIR.mkdir(parents=True, exist_ok=True)

# Color palette per region
COLOR_MAP = {
    "Mediterranean": "#4073ff",
    "Tamil/Indus": "#ff6347",
    "Egyptian": "#e0b200",
    "Mesopotamian": "#65a600",
    "Other": "#999999"
}

# Shape map per harmonic ratio (simplified)
SHAPE_MAP = {
    "3:2": "spiral",
    "5:3": "serpent",
    "2:1": "wave",
    "7:4": "sunburst",
    "4:3": "cross",
    "1:1": "circle"
}

def draw_shape(shape, color):
    """Return SVG path snippet for the given placeholder type."""
    if shape == "circle":
        return f'<circle cx="100" cy="100" r="70" fill="none" stroke="{color}" stroke-width="5"/>'
    elif shape == "spiral":
        path = []
        for i in range(0, 720, 10):
            angle = math.radians(i)
            r = i / 10
            x = 100 + r * math.cos(angle)
            y = 100 + r * math.sin(angle)
            path.append(f"{x},{y}")
        return f'<polyline points="{" ".join(path)}" fill="none" stroke="{color}" stroke-width="3"/>'
    elif shape == "serpent":
        pts = " ".join([f"{10*i},{100+30*math.sin(i/2)}" for i in range(0,20)])
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="4"/>'
    elif shape == "wave":
        pts = " ".join([f"{10*i},{100+40*math.sin(i/2)}" for i in range(0,20)])
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"/>'
    elif shape == "sunburst":
        rays = []
        for i in range(0,360,15):
            a = math.radians(i)
            x = 100 + 70 * math.cos(a)
            y = 100 + 70 * math.sin(a)
            rays.append(f'<line x1="100" y1="100" x2="{x}" y2="{y}" stroke="{color}" stroke-width="2"/>')
        return "\n".join(rays)
    elif shape == "cross":
        return (f'<line x1="30" y1="100" x2="170" y2="100" stroke="{color}" stroke-width="6"/>'
                f'<line x1="100" y1="30" x2="100" y2="170" stroke="{color}" stroke-width="6"/>')
    else:
        return f'<rect x="40" y="40" width="120" height="120" fill="none" stroke="{color}" stroke-width="4"/>'

def generate_svg(motif_id, region, ratio, cluster):
    """Generate a complete SVG string."""
    color = COLOR_MAP.get(region, "#888")
    shape = SHAPE_MAP.get(ratio, "circle")
    geom = draw_shape(shape, color)
    label = f"{motif_id} ({region})"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
<rect width="200" height="200" fill="white"/>
{geom}
<text x="100" y="190" font-size="14" text-anchor="middle" fill="#444">{label}</text>
</svg>'''

def main():
    df = pd.read_csv(CSV_PATH)
    for _, row in df.iterrows():
        motif_id = str(row["id"])
        region = str(row.get("culture_region", "Other"))
        ratio = str(row.get("harmonic_ratio", "1:1"))
        cluster = str(row.get("frequency_cluster", "C1"))
        svg = generate_svg(motif_id, region, ratio, cluster)
        file_path = IMG_DIR / f"{motif_id}.svg"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"Generated {len(df)} SVG placeholders in {IMG_DIR}/")

if __name__ == "__main__":
    main()
