#!/usr/bin/env python3
"""
SVG Font Preview Generator

Generates compressed SVG previews for Google Fonts using glyph path extraction.
Creates minimal SVG files showing font characteristics for preview purposes.

Cem Baspinar, 2025, MIT License.
"""

import os
import json
import gzip
import base64
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import RecordingPen
from tqdm import tqdm
import xml.etree.ElementTree as ET


class SVGPreviewGenerator:
    def __init__(self, database_file="font-database.json"):
        self.database_file = database_file
        
        # Preview configuration will use font family name
        self.font_size = 48
        self.svg_width = 200  # Increased width for font names
        self.svg_height = 60
        
        # Load font database
        with open(database_file, 'r', encoding='utf-8') as f:
            self.database = json.load(f)
    
    def extract_glyph_paths(self, font_path, text):
        """Extract SVG paths for the given text from a font file"""
        try:
            font = TTFont(font_path)
            glyph_set = font.getGlyphSet()
            cmap = font.getBestCmap()
            
            paths = []
            x_offset = 0
            
            for char in text:
                char_code = ord(char)
                if char_code not in cmap:
                    # Use space for missing characters
                    x_offset += self.font_size * 0.3
                    continue
                
                glyph_name = cmap[char_code]
                if glyph_name not in glyph_set:
                    x_offset += self.font_size * 0.3
                    continue
                
                glyph = glyph_set[glyph_name]
                
                # Record glyph outline
                recorder = RecordingPen()
                glyph.draw(recorder)
                
                # Convert to SVG path
                svg_pen = SVGPathPen(glyph_set)
                glyph.draw(svg_pen)
                
                # Get path data
                path_data = svg_pen.getCommands()
                if path_data.strip():
                    # Scale and position the glyph
                    scale = self.font_size / font['head'].unitsPerEm
                    
                    paths.append({
                        'path': path_data,
                        'x': x_offset,
                        'scale': scale,
                        'char': char
                    })
                
                # Advance x position
                advance_width = glyph.width if hasattr(glyph, 'width') else 500
                x_offset += advance_width * scale
            
            font.close()
            return paths
            
        except Exception as e:
            print(f"Error extracting paths from {font_path}: {e}")
            return []
    
    def create_svg_preview(self, paths, family_name):
        """Create optimized SVG preview from glyph paths"""
        if not paths:
            return None
        
        # Calculate viewBox
        total_width = max(path['x'] for path in paths) if paths else self.svg_width
        total_width = min(total_width, self.svg_width)
        
        # Create minimal SVG with white fill for easier color modulation
        svg_content = f'<svg viewBox="0 0 {total_width:.0f} {self.svg_height}" xmlns="http://www.w3.org/2000/svg">'
        
        for path_info in paths:
            if not path_info['path'].strip():
                continue
                
            # Transform path: scale and translate
            transform = f"translate({path_info['x']:.1f},{self.svg_height*0.8}) scale({path_info['scale']:.3f},-{path_info['scale']:.3f})"
            
            # Add path element with white fill
            svg_content += f'<path d="{path_info["path"]}" transform="{transform}" fill="white"/>'
        
        svg_content += '</svg>'
        
        # Optimize SVG content
        return self.optimize_svg(svg_content)
    
    def optimize_svg(self, svg_content):
        """Optimize SVG content for minimal size"""
        # Remove unnecessary whitespace and precision
        import re
        
        # Reduce floating point precision
        svg_content = re.sub(r'(\d+\.\d{3})\d+', r'\1', svg_content)
        
        # Remove unnecessary spaces
        svg_content = re.sub(r'\s+', ' ', svg_content)
        svg_content = re.sub(r'> <', '><', svg_content)
        
        # Remove empty path elements
        svg_content = re.sub(r'<path d=""\s*[^>]*>', '', svg_content)
        
        return svg_content.strip()
    
    def compress_svg(self, svg_content):
        """Compress SVG content using gzip and encode as base64"""
        # Gzip compress
        compressed = gzip.compress(svg_content.encode('utf-8'), compresslevel=9)
        
        # Base64 encode for JSON storage
        encoded = base64.b64encode(compressed).decode('ascii')
        
        return encoded
    
    def generate_previews(self):
        """Generate SVG previews for all fonts in the database"""
        fonts = self.database.get("fonts", {})
        print(f"Generating SVG previews for {len(fonts)} font families...")
        
        preview_data = {}
        successful_previews = 0
        total_size = 0
        
        for family_name, font_data in tqdm(fonts.items(), desc="Generating previews"):
            # Get first regular variant
            variants = font_data.get("variants", [])
            regular_variant = None
            
            # Prefer regular weight, normal style
            for variant in variants:
                if variant.get("weight") == 400 and variant.get("style") == "normal":
                    regular_variant = variant
                    break
            
            # Fallback to first variant
            if not regular_variant and variants:
                regular_variant = variants[0]
            
            if not regular_variant:
                continue
            
            # Download URL to local path conversion
            download_url = regular_variant.get("download_url", "")
            if not download_url:
                continue
            
            # Construct local font path
            url_path = download_url.replace("https://raw.githubusercontent.com/google/fonts/main/", "")
            font_path = Path("google-fonts-source") / url_path
            
            if not font_path.exists():
                continue
            
            # Use font family name as preview text (truncated if too long)
            preview_text = family_name
            if len(preview_text) > 12:  # Limit length to fit in SVG
                preview_text = preview_text[:12]
            
            # Extract glyph paths
            paths = self.extract_glyph_paths(font_path, preview_text)
            if not paths:
                continue
            
            # Create SVG preview
            svg_content = self.create_svg_preview(paths, family_name)
            if not svg_content:
                continue
            
            # Compress SVG
            compressed_svg = self.compress_svg(svg_content)
            
            # Store preview data
            preview_data[family_name] = {
                "svg_compressed": compressed_svg,
                "original_size": len(svg_content),
                "compressed_size": len(compressed_svg),
                "preview_text": preview_text
            }
            
            # Note: SVG files are stored compressed in database only
            # No individual files are saved to keep repository size minimal
            
            successful_previews += 1
            total_size += len(compressed_svg)
        
        print(f"Generated {successful_previews} SVG previews")
        print(f"Total compressed size: {total_size / 1024:.1f} KB")
        print(f"Average size per preview: {total_size / successful_previews if successful_previews > 0 else 0:.0f} bytes")
        
        return preview_data
    
    def update_database(self, preview_data):
        """Update the font database with SVG preview data"""
        print("Updating database with preview data...")
        
        fonts = self.database.get("fonts", {})
        updated_count = 0
        
        for family_name, preview_info in preview_data.items():
            if family_name in fonts:
                fonts[family_name]["preview"] = {
                    "svg_compressed": preview_info["svg_compressed"],
                    "compressed_size": preview_info["compressed_size"],
                    "preview_text": preview_info["preview_text"]
                }
                updated_count += 1
        
        # Update database metadata
        self.database["preview_stats"] = {
            "total_previews": len(preview_data),
            "total_compressed_size": sum(p["compressed_size"] for p in preview_data.values()),
            "average_size": sum(p["compressed_size"] for p in preview_data.values()) / len(preview_data) if preview_data else 0
        }
        
        # Save updated database
        with open(self.database_file, 'w', encoding='utf-8') as f:
            json.dump(self.database, f, indent=2, ensure_ascii=False)
        
        print(f"Updated {updated_count} font entries with preview data")
        
        # Print final statistics
        total_db_size = Path(self.database_file).stat().st_size
        preview_size = self.database["preview_stats"]["total_compressed_size"]
        
        print(f"Database size: {total_db_size / 1024:.1f} KB")
        print(f"Preview data size: {preview_size / 1024:.1f} KB ({preview_size / total_db_size * 100:.1f}% of total)")


def main():
    """Main execution function"""
    if not Path("font-database.json").exists():
        print("Error: font-database.json not found!")
        print("Run generate_metadata.py first to create the font database.")
        return 1
    
    if not Path("google-fonts-source").exists():
        print("Error: google-fonts-source directory not found!")
        print("Make sure the Google Fonts repository is cloned.")
        return 1
    
    generator = SVGPreviewGenerator()
    preview_data = generator.generate_previews()
    
    if preview_data:
        generator.update_database(preview_data)
        print("SVG preview generation completed successfully!")
    else:
        print("No previews were generated. Check font files and paths.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
