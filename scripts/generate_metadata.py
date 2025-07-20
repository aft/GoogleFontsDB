#!/usr/bin/env python3
"""
Google Fonts Metadata Extraction Script

Processes the Google Fonts repository to extract font metadata including:
- Font family names and categories
- Available weights and styles
- File paths and download URLs
- Font licensing information

Cem Baspinar, 2025, MIT License.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
import re
from fontTools.ttLib import TTFont
from tqdm import tqdm


class GoogleFontsProcessor:
    def __init__(self, source_dir="google-fonts-source", output_file="font-database.json"):
        self.source_dir = Path(source_dir)
        self.output_file = output_file
        self.base_url = "https://raw.githubusercontent.com/google/fonts/main"
        self.font_database = {
            "version": datetime.now().strftime("%Y.%m.%d"),
            "updated": datetime.now().isoformat() + "Z",
            "total_families": 0,
            "fonts": {}
        }
        
    def extract_font_metadata(self, font_path):
        """Extract metadata from a font file"""
        try:
            font = TTFont(font_path)
            
            # Get font family name
            name_table = font['name']
            family_name = None
            subfamily_name = None
            
            for record in name_table.names:
                if record.nameID == 1:  # Font Family
                    family_name = record.toUnicode()
                elif record.nameID == 2:  # Font Subfamily (style)
                    subfamily_name = record.toUnicode()
                    
                if family_name and subfamily_name:
                    break
            
            if not family_name:
                return None
                
            # Parse weight and style from subfamily or filename
            weight, style = self.parse_weight_style(subfamily_name, font_path.name)
            
            # Get font metrics
            try:
                os_2_table = font['OS/2']
                weight_class = os_2_table.usWeightClass if hasattr(os_2_table, 'usWeightClass') else 400
            except KeyError:
                weight_class = 400
                
            return {
                "family": family_name,
                "subfamily": subfamily_name,
                "weight": weight,
                "style": style,
                "weight_class": weight_class,
                "file_size": font_path.stat().st_size,
                "file_path": str(font_path.relative_to(self.source_dir)),
                "download_url": f"{self.base_url}/{font_path.relative_to(self.source_dir)}"
            }
            
        except Exception as e:
            print(f"Error processing {font_path}: {e}")
            return None
        finally:
            if 'font' in locals():
                font.close()
    
    def parse_weight_style(self, subfamily, filename):
        """Parse weight and style from subfamily name or filename"""
        subfamily = subfamily.lower() if subfamily else ""
        filename = filename.lower()
        
        # Weight mapping
        weight_map = {
            'thin': 100, 'hairline': 100,
            'extralight': 200, 'ultralight': 200,
            'light': 300,
            'regular': 400, 'normal': 400, 'book': 400,
            'medium': 500,
            'semibold': 600, 'demibold': 600,
            'bold': 700,
            'extrabold': 800, 'ultrabold': 800,
            'black': 900, 'heavy': 900
        }
        
        # Extract weight
        weight = 400  # default
        for weight_name, weight_value in weight_map.items():
            if weight_name in subfamily or weight_name in filename:
                weight = weight_value
                break
        
        # Extract style
        style = "normal"
        if "italic" in subfamily or "italic" in filename:
            style = "italic"
        elif "oblique" in subfamily or "oblique" in filename:
            style = "oblique"
            
        return weight, style
    
    def get_font_category(self, font_path):
        """Determine font category from directory structure"""
        path_parts = font_path.parts
        
        # Category mapping based on Google Fonts directory structure
        if "ofl" in path_parts:
            # Open Font License - most diverse category
            font_name = path_parts[-2].lower()
            
            # Serif fonts
            if any(keyword in font_name for keyword in [
                'serif', 'times', 'georgia', 'playfair', 'lora', 'merriweather',
                'crimson', 'libre', 'spectral', 'vollkorn', 'bitter'
            ]):
                return "serif"
            
            # Display fonts
            elif any(keyword in font_name for keyword in [
                'display', 'fancy', 'decorative', 'title', 'headline',
                'lobster', 'pacifico', 'righteous', 'fredoka'
            ]):
                return "display"
            
            # Handwriting fonts
            elif any(keyword in font_name for keyword in [
                'handwriting', 'script', 'cursive', 'hand', 'dancing',
                'satisfy', 'allura', 'great vibes', 'caveat'
            ]):
                return "handwriting"
            
            # Monospace fonts
            elif any(keyword in font_name for keyword in [
                'mono', 'code', 'inconsolata', 'source code', 'jetbrains',
                'fira code', 'roboto mono', 'ubuntu mono'
            ]):
                return "monospace"
            
            # Default to sans-serif for OFL
            return "sans-serif"
            
        elif "apache" in path_parts:
            # Apache licensed fonts - mostly sans-serif
            return "sans-serif"
        elif "ufl" in path_parts:
            # Ubuntu Font License
            return "sans-serif"
        else:
            # Default category
            return "sans-serif"
    
    def process_fonts(self):
        """Process all font files in the Google Fonts repository"""
        print("Scanning for font files...")
        
        # Find all TTF files
        font_files = list(self.source_dir.rglob("*.ttf"))
        print(f"Found {len(font_files)} font files")
        
        processed_families = {}
        
        for font_path in tqdm(font_files, desc="Processing fonts"):
            metadata = self.extract_font_metadata(font_path)
            if not metadata:
                continue
                
            family_name = metadata["family"]
            category = self.get_font_category(font_path)
            
            # Initialize family entry
            if family_name not in processed_families:
                processed_families[family_name] = {
                    "category": category,
                    "variants": [],
                    "license": self.get_license_info(font_path)
                }
            
            # Add variant
            variant = {
                "weight": metadata["weight"],
                "style": metadata["style"],
                "weight_class": metadata["weight_class"],
                "file_size": metadata["file_size"],
                "download_url": metadata["download_url"]
            }
            
            processed_families[family_name]["variants"].append(variant)
        
        # Sort variants by weight and style
        for family_data in processed_families.values():
            family_data["variants"].sort(key=lambda v: (v["weight"], v["style"]))
        
        self.font_database["fonts"] = processed_families
        self.font_database["total_families"] = len(processed_families)
        
        print(f"Processed {len(processed_families)} font families")
        return processed_families
    
    def get_license_info(self, font_path):
        """Extract license information for the font"""
        # Look for license files in the font's directory
        font_dir = font_path.parent
        
        license_files = ["OFL.txt", "LICENSE.txt", "LICENCE.txt", "UFL.txt"]
        for license_file in license_files:
            license_path = font_dir / license_file
            if license_path.exists():
                return {
                    "type": license_file.split('.')[0],
                    "url": f"{self.base_url}/{license_path.relative_to(self.source_dir)}"
                }
        
        # Default license based on directory
        if "ofl" in font_path.parts:
            return {"type": "OFL", "url": "https://scripts.sil.org/OFL"}
        elif "apache" in font_path.parts:
            return {"type": "Apache", "url": "https://www.apache.org/licenses/LICENSE-2.0"}
        elif "ufl" in font_path.parts:
            return {"type": "UFL", "url": "https://www.ubuntu.com/legal/terms-and-policies/font-licence"}
        
        return {"type": "Open Source", "url": ""}
    
    def save_database(self):
        """Save the font database to JSON file"""
        print(f"Saving database to {self.output_file}...")
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.font_database, f, indent=2, ensure_ascii=False)
        
        # Print statistics
        db_size = Path(self.output_file).stat().st_size
        print("Database saved successfully!")
        print(f"- Font families: {self.font_database['total_families']}")
        print(f"- Database size: {db_size / 1024:.1f} KB")
        
        # Category breakdown
        categories = {}
        for font_data in self.font_database["fonts"].values():
            category = font_data["category"]
            categories[category] = categories.get(category, 0) + 1
        
        print("Category breakdown:")
        for category, count in sorted(categories.items()):
            print(f"  - {category}: {count} families")


def main():
    """Main execution function"""
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    else:
        source_dir = "google-fonts-source"
    
    if not Path(source_dir).exists():
        print(f"Error: Source directory '{source_dir}' not found!")
        print("Make sure you've cloned the Google Fonts repository first.")
        sys.exit(1)
    
    processor = GoogleFontsProcessor(source_dir)
    processor.process_fonts()
    processor.save_database()
    
    print("Font metadata extraction completed successfully!")


if __name__ == "__main__":
    main()