# Single-form variants

Each of the 67 original generated stills now has a **single dominant centered shape** variant, rendered as 1254×1254 neon-gradient wireframe geometry on black. These are *deterministic geometric reinterpretations* of the patterns, not pixel-identical edits of the earlier AI-generated raster artwork.

The original 2D tilings, 3D lattices, and 4D hypercube patterns are preserved unchanged under `renders/stills/`. New assets live under `renders/stills-single/`, with optimized WebP previews under `renders/thumbnails-single/`.

The generator source is `generators/single-forms/render_single_forms.py`. It requires `Pillow` and reads original PNG filenames as its pattern inventory. Its output is deterministic based on the relative file path. Run it from the repo root:

```bash
python3 -m pip install Pillow
python3 generators/single-forms/render_single_forms.py --source renders/stills --output renders/stills-single --thumbnails renders/thumbnails-single
```

## Gallery

### 2D shapes and geometric patterns

| ![Continuous rainbow lattice on black](renders/thumbnails-single/2d/Continuous%20rainbow%20lattice%20on%20black.webp) | ![Diagonal rainbow heptagon lattice](renders/thumbnails-single/2d/Diagonal%20rainbow%20heptagon%20lattice.webp) | ![Diagonal rainbow square grid](renders/thumbnails-single/2d/Diagonal%20rainbow%20square%20grid.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Continuous%20rainbow%20lattice%20on%20black.png) | [Open PNG](renders/stills-single/2d/Diagonal%20rainbow%20heptagon%20lattice.png) | [Open PNG](renders/stills-single/2d/Diagonal%20rainbow%20square%20grid.png) |

| ![Hairline rainbow spiral wireframe](renders/thumbnails-single/2d/Hairline%20rainbow%20spiral%20wireframe.webp) | ![Neon Penrose Rhombi on Black](renders/thumbnails-single/2d/Neon%20Penrose%20Rhombi%20on%20Black.webp) | ![Neon Rainbow Triangle Lattice](renders/thumbnails-single/2d/Neon%20Rainbow%20Triangle%20Lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Hairline%20rainbow%20spiral%20wireframe.png) | [Open PNG](renders/stills-single/2d/Neon%20Penrose%20Rhombi%20on%20Black.png) | [Open PNG](renders/stills-single/2d/Neon%20Rainbow%20Triangle%20Lattice.png) |

| ![Neon Rainbow Triangle Tessellation](renders/thumbnails-single/2d/Neon%20Rainbow%20Triangle%20Tessellation.webp) | ![Neon Triangular Pinwheels on Black](renders/thumbnails-single/2d/Neon%20Triangular%20Pinwheels%20on%20Black.webp) | ![Neon Truchet Curves on Black](renders/thumbnails-single/2d/Neon%20Truchet%20Curves%20on%20Black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Neon%20Rainbow%20Triangle%20Tessellation.png) | [Open PNG](renders/stills-single/2d/Neon%20Triangular%20Pinwheels%20on%20Black.png) | [Open PNG](renders/stills-single/2d/Neon%20Truchet%20Curves%20on%20Black.png) |

| ![Neon broken rings on black](renders/thumbnails-single/2d/Neon%20broken%20rings%20on%20black.webp) | ![Neon herringbone geometry on black](renders/thumbnails-single/2d/Neon%20herringbone%20geometry%20on%20black.webp) | ![Neon maze lattice on black](renders/thumbnails-single/2d/Neon%20maze%20lattice%20on%20black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Neon%20broken%20rings%20on%20black.png) | [Open PNG](renders/stills-single/2d/Neon%20herringbone%20geometry%20on%20black.png) | [Open PNG](renders/stills-single/2d/Neon%20maze%20lattice%20on%20black.png) |

| ![Neon pentagon tessellation on black](renders/thumbnails-single/2d/Neon%20pentagon%20tessellation%20on%20black.webp) | ![Neon rainbow decagons on black](renders/thumbnails-single/2d/Neon%20rainbow%20decagons%20on%20black.webp) | ![Neon rainbow hendecagon lattice(1)](renders/thumbnails-single/2d/Neon%20rainbow%20hendecagon%20lattice%281%29.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Neon%20pentagon%20tessellation%20on%20black.png) | [Open PNG](renders/stills-single/2d/Neon%20rainbow%20decagons%20on%20black.png) | [Open PNG](renders/stills-single/2d/Neon%20rainbow%20hendecagon%20lattice%281%29.png) |

| ![Neon rainbow hendecagon lattice](renders/thumbnails-single/2d/Neon%20rainbow%20hendecagon%20lattice.webp) | ![Neon rainbow honeycomb geometry](renders/thumbnails-single/2d/Neon%20rainbow%20honeycomb%20geometry.webp) | ![Neon rainbow octagon lattice](renders/thumbnails-single/2d/Neon%20rainbow%20octagon%20lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Neon%20rainbow%20hendecagon%20lattice.png) | [Open PNG](renders/stills-single/2d/Neon%20rainbow%20honeycomb%20geometry.png) | [Open PNG](renders/stills-single/2d/Neon%20rainbow%20octagon%20lattice.png) |

| ![Neon rainbow square lattice](renders/thumbnails-single/2d/Neon%20rainbow%20square%20lattice.webp) | ![Neon rainbow tangent circle lattice](renders/thumbnails-single/2d/Neon%20rainbow%20tangent%20circle%20lattice.webp) | ![Rainbow Circle Mosaic on Black](renders/thumbnails-single/2d/Rainbow%20Circle%20Mosaic%20on%20Black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Neon%20rainbow%20square%20lattice.png) | [Open PNG](renders/stills-single/2d/Neon%20rainbow%20tangent%20circle%20lattice.png) | [Open PNG](renders/stills-single/2d/Rainbow%20Circle%20Mosaic%20on%20Black.png) |

| ![Rainbow D20 Hexagonal Linework](renders/thumbnails-single/2d/Rainbow%20D20%20Hexagonal%20Linework.webp) | ![Rainbow Decagon Lattice on Black](renders/thumbnails-single/2d/Rainbow%20Decagon%20Lattice%20on%20Black.webp) | ![Rainbow Nonagons on Black](renders/thumbnails-single/2d/Rainbow%20Nonagons%20on%20Black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Rainbow%20D20%20Hexagonal%20Linework.png) | [Open PNG](renders/stills-single/2d/Rainbow%20Decagon%20Lattice%20on%20Black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20Nonagons%20on%20Black.png) |

| ![Rainbow Truchet curves on black](renders/thumbnails-single/2d/Rainbow%20Truchet%20curves%20on%20black.webp) | ![Rainbow concentric arcs on black](renders/thumbnails-single/2d/Rainbow%20concentric%20arcs%20on%20black.webp) | ![Rainbow dodecagon lattice on black(1)](renders/thumbnails-single/2d/Rainbow%20dodecagon%20lattice%20on%20black%281%29.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Rainbow%20Truchet%20curves%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20concentric%20arcs%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20dodecagon%20lattice%20on%20black%281%29.png) |

| ![Rainbow dodecagon lattice on black](renders/thumbnails-single/2d/Rainbow%20dodecagon%20lattice%20on%20black.webp) | ![Rainbow heptagon lattice on black](renders/thumbnails-single/2d/Rainbow%20heptagon%20lattice%20on%20black.webp) | ![Rainbow hexagon honeycomb on black](renders/thumbnails-single/2d/Rainbow%20hexagon%20honeycomb%20on%20black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Rainbow%20dodecagon%20lattice%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20heptagon%20lattice%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20hexagon%20honeycomb%20on%20black.png) |

| ![Rainbow hexagon lattice on black](renders/thumbnails-single/2d/Rainbow%20hexagon%20lattice%20on%20black.webp) | ![Rainbow nonagon lattice on black](renders/thumbnails-single/2d/Rainbow%20nonagon%20lattice%20on%20black.webp) | ![Rainbow octagonal wireframe lattice](renders/thumbnails-single/2d/Rainbow%20octagonal%20wireframe%20lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Rainbow%20hexagon%20lattice%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20nonagon%20lattice%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20octagonal%20wireframe%20lattice.png) |

| ![Rainbow octagons on black](renders/thumbnails-single/2d/Rainbow%20octagons%20on%20black.webp) | ![Rainbow pentagon lattice on black(1)](renders/thumbnails-single/2d/Rainbow%20pentagon%20lattice%20on%20black%281%29.webp) | ![Rainbow pentagon lattice on black](renders/thumbnails-single/2d/Rainbow%20pentagon%20lattice%20on%20black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Rainbow%20octagons%20on%20black.png) | [Open PNG](renders/stills-single/2d/Rainbow%20pentagon%20lattice%20on%20black%281%29.png) | [Open PNG](renders/stills-single/2d/Rainbow%20pentagon%20lattice%20on%20black.png) |

| ![Rainbow square spirals on black(1)](renders/thumbnails-single/2d/Rainbow%20square%20spirals%20on%20black%281%29.webp) | ![Rainbow square spirals on black](renders/thumbnails-single/2d/Rainbow%20square%20spirals%20on%20black.webp) | ![Sparse Neon Octagon Lattice](renders/thumbnails-single/2d/Sparse%20Neon%20Octagon%20Lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/2d/Rainbow%20square%20spirals%20on%20black%281%29.png) | [Open PNG](renders/stills-single/2d/Rainbow%20square%20spirals%20on%20black.png) | [Open PNG](renders/stills-single/2d/Sparse%20Neon%20Octagon%20Lattice.png) |

### 3D Platonic solids and wireframes

| ![Diagonal rainbow dodecahedron lattice](renders/thumbnails-single/3d/Diagonal%20rainbow%20dodecahedron%20lattice.webp) | ![Full-spectrum isometric cube lattice](renders/thumbnails-single/3d/Full-spectrum%20isometric%20cube%20lattice.webp) | ![Neon Rainbow Tetrahedron Lattice](renders/thumbnails-single/3d/Neon%20Rainbow%20Tetrahedron%20Lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/3d/Diagonal%20rainbow%20dodecahedron%20lattice.png) | [Open PNG](renders/stills-single/3d/Full-spectrum%20isometric%20cube%20lattice.png) | [Open PNG](renders/stills-single/3d/Neon%20Rainbow%20Tetrahedron%20Lattice.png) |

| ![Neon cube lattice in black](renders/thumbnails-single/3d/Neon%20cube%20lattice%20in%20black.webp) | ![Neon rainbow icosahedra in hexagonal array](renders/thumbnails-single/3d/Neon%20rainbow%20icosahedra%20in%20hexagonal%20array.webp) | ![Neon rainbow isometric cube lattice](renders/thumbnails-single/3d/Neon%20rainbow%20isometric%20cube%20lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/3d/Neon%20cube%20lattice%20in%20black.png) | [Open PNG](renders/stills-single/3d/Neon%20rainbow%20icosahedra%20in%20hexagonal%20array.png) | [Open PNG](renders/stills-single/3d/Neon%20rainbow%20isometric%20cube%20lattice.png) |

| ![Neon rainbow octahedron lattice(1)](renders/thumbnails-single/3d/Neon%20rainbow%20octahedron%20lattice%281%29.webp) | ![Neon rainbow octahedron lattice](renders/thumbnails-single/3d/Neon%20rainbow%20octahedron%20lattice.webp) | ![Rainbow Octahedron Wireframe Constellation](renders/thumbnails-single/3d/Rainbow%20Octahedron%20Wireframe%20Constellation.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/3d/Neon%20rainbow%20octahedron%20lattice%281%29.png) | [Open PNG](renders/stills-single/3d/Neon%20rainbow%20octahedron%20lattice.png) | [Open PNG](renders/stills-single/3d/Rainbow%20Octahedron%20Wireframe%20Constellation.png) |

| ![Rainbow Octahedron on a Black Grid](renders/thumbnails-single/3d/Rainbow%20Octahedron%20on%20a%20Black%20Grid.webp) | ![Rainbow cube wireframes on black](renders/thumbnails-single/3d/Rainbow%20cube%20wireframes%20on%20black.webp) | ![Rainbow dodecahedra on black](renders/thumbnails-single/3d/Rainbow%20dodecahedra%20on%20black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/3d/Rainbow%20Octahedron%20on%20a%20Black%20Grid.png) | [Open PNG](renders/stills-single/3d/Rainbow%20cube%20wireframes%20on%20black.png) | [Open PNG](renders/stills-single/3d/Rainbow%20dodecahedra%20on%20black.png) |

| ![Rainbow dodecahedron wireframe grid](renders/thumbnails-single/3d/Rainbow%20dodecahedron%20wireframe%20grid.webp) | ![Rainbow octahedron wireframes on black](renders/thumbnails-single/3d/Rainbow%20octahedron%20wireframes%20on%20black.webp) | ![Rainbow tetrahedron lattice](renders/thumbnails-single/3d/Rainbow%20tetrahedron%20lattice.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/3d/Rainbow%20dodecahedron%20wireframe%20grid.png) | [Open PNG](renders/stills-single/3d/Rainbow%20octahedron%20wireframes%20on%20black.png) | [Open PNG](renders/stills-single/3d/Rainbow%20tetrahedron%20lattice.png) |

| ![Rainbow wireframe cube lattice](renders/thumbnails-single/3d/Rainbow%20wireframe%20cube%20lattice.webp) | ![Rainbow wireframe icosahedra on black](renders/thumbnails-single/3d/Rainbow%20wireframe%20icosahedra%20on%20black.webp) | ![Rainbow wireframe icosahedrons on black](renders/thumbnails-single/3d/Rainbow%20wireframe%20icosahedrons%20on%20black.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/3d/Rainbow%20wireframe%20cube%20lattice.png) | [Open PNG](renders/stills-single/3d/Rainbow%20wireframe%20icosahedra%20on%20black.png) | [Open PNG](renders/stills-single/3d/Rainbow%20wireframe%20icosahedrons%20on%20black.png) |

| ![Rainbow wireframe tetrahedron lattice](renders/thumbnails-single/3d/Rainbow%20wireframe%20tetrahedron%20lattice.webp) | ![Staggered neon rainbow dodecahedra](renders/thumbnails-single/3d/Staggered%20neon%20rainbow%20dodecahedra.webp) |
| :---: | :---: |
| [Open PNG](renders/stills-single/3d/Rainbow%20wireframe%20tetrahedron%20lattice.png) | [Open PNG](renders/stills-single/3d/Staggered%20neon%20rainbow%20dodecahedra.png) |

### 4D tesseract projections

| ![Full-spectrum neon tesseract grid](renders/thumbnails-single/4d/Full-spectrum%20neon%20tesseract%20grid.webp) | ![Neon Rainbow Tesseract Grid](renders/thumbnails-single/4d/Neon%20Rainbow%20Tesseract%20Grid.webp) | ![Neon Rainbow Tesseract Wallpaper](renders/thumbnails-single/4d/Neon%20Rainbow%20Tesseract%20Wallpaper.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/4d/Full-spectrum%20neon%20tesseract%20grid.png) | [Open PNG](renders/stills-single/4d/Neon%20Rainbow%20Tesseract%20Grid.png) | [Open PNG](renders/stills-single/4d/Neon%20Rainbow%20Tesseract%20Wallpaper.png) |

| ![Neon rainbow tesseract lattice](renders/thumbnails-single/4d/Neon%20rainbow%20tesseract%20lattice.webp) | ![Neon rainbow tesseract pattern(1)](renders/thumbnails-single/4d/Neon%20rainbow%20tesseract%20pattern%281%29.webp) | ![Neon rainbow tesseract pattern](renders/thumbnails-single/4d/Neon%20rainbow%20tesseract%20pattern.webp) |
| :---: | :---: | :---: |
| [Open PNG](renders/stills-single/4d/Neon%20rainbow%20tesseract%20lattice.png) | [Open PNG](renders/stills-single/4d/Neon%20rainbow%20tesseract%20pattern%281%29.png) | [Open PNG](renders/stills-single/4d/Neon%20rainbow%20tesseract%20pattern.png) |

| ![Neon rainbow tesseract wireframe grid](renders/thumbnails-single/4d/Neon%20rainbow%20tesseract%20wireframe%20grid.webp) | ![Octagonal Neon Rainbow Tesseract](renders/thumbnails-single/4d/Octagonal%20Neon%20Rainbow%20Tesseract.webp) |
| :---: | :---: |
| [Open PNG](renders/stills-single/4d/Neon%20rainbow%20tesseract%20wireframe%20grid.png) | [Open PNG](renders/stills-single/4d/Octagonal%20Neon%20Rainbow%20Tesseract.png) |

