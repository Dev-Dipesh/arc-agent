## Generate Diagram PNGs from PlantUML

Script:

- `docs/script/generate-diagram-pngs.cjs`

Source folder:

- `docs/script/puml/*.puml`

Output folder:

- `docs/script/diagrams/*.png`

Commands:

```bash
# Install script package metadata (no runtime deps needed)
cd docs/script
npm install

# Render all .puml files
npm run diagrams:generate

# Render one diagram only
npm run diagrams:generate:one -- arc-agent-1.puml
```

Notes:

- The script uses Kroki (`https://kroki.io/plantuml/png`), so internet access is required.
- Output PNG keeps the same base filename as the input `.puml`.
