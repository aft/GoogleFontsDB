# Google Fonts Database

Automated processing pipeline for creating optimized Google Fonts metadata and preview database for use in applications and editors.

## Overview

This repository automatically processes the [Google Fonts repository](https://github.com/google/fonts) to generate:

- **Comprehensive font metadata** with family names, weights, styles, and categories
- **Compressed SVG previews** (~800KB total) for visual font selection
- **Optimized database formats** with multiple index files for different use cases
- **Quality validation** and integrity checks
- **Performance statistics** and analytics

The database is updated monthly via GitHub Actions and provides a lightweight, cached solution for applications that need access to Google Fonts metadata without downloading the entire 1GB+ fonts repository.

## Features

### 🤖 Automated Processing
- **Monthly updates** via GitHub Actions from the official Google Fonts repository
- **Intelligent categorization** based on font characteristics and directory structure
- **SVG preview generation** using glyph path extraction for minimal file sizes
- **Database optimization** with deduplication and compression

### 📊 Multiple Output Formats
- **Main database**: Complete font metadata with all variants
- **Family index**: Font family names only (for autocomplete)
- **Category index**: Fonts organized by category (serif, sans-serif, display, etc.)
- **Popular fonts**: Most comprehensive font families
- **Compressed versions**: Gzip-compressed databases for bandwidth optimization

### ✅ Quality Assurance
- **Comprehensive validation** of all generated data
- **Integrity checks** with SHA256 checksums
- **Error reporting** and quality metrics
- **Performance benchmarks** and statistics

## Database Structure

### Main Database (`font-database.json`)
```json
{
  "version": "2025.01.20",
  "updated": "2025-01-20T02:15:30Z",
  "total_families": 1500,
  "fonts": {
    "Roboto": {
      "category": "sans-serif",
      "license": {"type": "Apache", "url": "..."},
      "variants": [
        {
          "weight": 400,
          "style": "normal",
          "download_url": "https://raw.githubusercontent.com/google/fonts/...",
          "file_size": 168000
        }
      ],
      "preview": {
        "svg_compressed": "H4sIAA...",
        "compressed_size": 245
      }
    }
  }
}
```

### Font Categories
- **serif**: Traditional serif fonts (Times, Georgia, etc.)
- **sans-serif**: Modern sans-serif fonts (Roboto, Open Sans, etc.)
- **display**: Decorative and headline fonts
- **handwriting**: Script and cursive fonts
- **monospace**: Fixed-width fonts for code

## Usage

### Direct Download
Download the latest database files from the [Releases](../../releases) page:

- `font-database.json` - Complete database
- `font-database.json.gz` - Compressed version
- `font-families-index.json` - Family names only
- `font-categories-index.json` - Categorized fonts
- `font-popular-index.json` - Most comprehensive families

### API Access
```javascript
// Fetch font families
const families = await fetch('https://raw.githubusercontent.com/aft/GoogleFontsDB/main/font-families-index.json')
  .then(r => r.json());

// Fetch complete database
const database = await fetch('https://raw.githubusercontent.com/aft/GoogleFontsDB/main/font-database.json')
  .then(r => r.json());
```

### SVG Preview Rendering
The database includes compressed SVG previews for visual font selection:

```javascript
// Decompress SVG preview
function decompressSVG(compressedData) {
  const binaryData = atob(compressedData);
  const compressed = new Uint8Array(binaryData.length);
  for (let i = 0; i < binaryData.length; i++) {
    compressed[i] = binaryData.charCodeAt(i);
  }
  return pako.inflate(compressed, { to: 'string' });
}

// Render font preview
const fontData = database.fonts['Roboto'];
const svgContent = decompressSVG(fontData.preview.svg_compressed);
document.getElementById('preview').innerHTML = svgContent;
```

## Technical Implementation

### Processing Pipeline
1. **Clone Google Fonts Repository** - Downloads latest font files
2. **Extract Metadata** - Analyzes TTF files for family names, weights, styles
3. **Generate Categories** - Intelligent categorization based on font characteristics
4. **Create SVG Previews** - Extract glyph paths and generate compressed previews
5. **Optimize Database** - Remove redundancy, compress data, create indexes
6. **Validate Output** - Quality assurance and integrity checks
7. **Generate Statistics** - Performance metrics and analytics

### Dependencies
- **fonttools**: TTF file analysis and glyph path extraction
- **Python 3.11**: Core processing language
- **GitHub Actions**: Automated monthly updates
- **Ubuntu Latest**: Processing environment

### Performance Metrics
- **Processing Time**: ~30 minutes for complete pipeline
- **Database Size**: ~2-5MB (depending on compression)
- **Preview Size**: ~800KB total for all SVG previews
- **Update Frequency**: Monthly (1st of each month at 2 AM UTC)

## Development

### Local Processing
```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Process fonts (requires Google Fonts repo)
python scripts/generate_metadata.py
python scripts/generate_svg_previews.py
python scripts/optimize_database.py
python scripts/validate_output.py
```

### GitHub Actions
The repository uses automated workflows for:
- **Monthly updates** from Google Fonts repository
- **Quality validation** of generated data
- **Release creation** with database artifacts
- **Performance monitoring** and statistics

## Integration Examples

### Godot Engine
Perfect for font selection panels in game engines and editors:
```gdscript
# Load font database
var http_request = HTTPRequest.new()
add_child(http_request)
http_request.request("https://raw.githubusercontent.com/aft/GoogleFontsDB/main/font-database.json")
var response = await http_request.request_completed
var database = JSON.parse_string(response[3].get_string_from_utf8())
```

### Web Applications
Ideal for font selection interfaces:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.0.4/pako.min.js"></script>
<script>
  // Use with any decompression library that supports gzip
  // Perfect for font selection dropdowns and preview interfaces
</script>
```

## Statistics

Latest database statistics are available in `stats.json`:
- Total font families
- Category breakdown
- File size analysis
- Preview coverage
- Quality metrics

## License

This project is licensed under the MIT License. The processed font data maintains the original Google Fonts licensing (primarily Open Font License).

Google Fonts are licensed under various open source licenses. Please check individual font licenses before use in your projects.

## Contributing

This is an automated processing repository. For font additions or changes, please contribute to the [Google Fonts repository](https://github.com/google/fonts).

For issues with the processing pipeline or database structure, please open an issue in this repository.