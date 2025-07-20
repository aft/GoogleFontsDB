#!/usr/bin/env python3
"""
Database Optimization Script

Optimizes the font database for size and performance:
- Removes unnecessary metadata
- Compresses large data structures
- Validates data integrity
- Creates optimized distribution files

Cem Baspinar, 2025, MIT License.
"""

import os
import json
import gzip
import hashlib
from pathlib import Path
from datetime import datetime


class DatabaseOptimizer:
    def __init__(self, database_file="font-database.json"):
        self.database_file = database_file
        self.optimized_file = "font-database-optimized.json"
        self.compressed_file = "font-database.json.gz"
        
        # Load database
        with open(database_file, 'r', encoding='utf-8') as f:
            self.database = json.load(f)
    
    def remove_redundant_metadata(self):
        """Remove redundant or unnecessary metadata to reduce size"""
        print("Removing redundant metadata...")
        
        fonts = self.database.get("fonts", {})
        removed_fields = 0
        
        for family_name, font_data in fonts.items():
            variants = font_data.get("variants", [])
            
            # Remove redundant file_size if all variants are similar size
            if len(variants) > 1:
                sizes = [v.get("file_size", 0) for v in variants]
                avg_size = sum(sizes) / len(sizes)
                
                # If all sizes are within 10% of average, store only average
                if all(abs(size - avg_size) / avg_size < 0.1 for size in sizes if size > 0):
                    font_data["avg_file_size"] = int(avg_size)
                    for variant in variants:
                        if "file_size" in variant:
                            del variant["file_size"]
                            removed_fields += 1
            
            # Remove weight_class if it matches standard weight
            for variant in variants:
                weight = variant.get("weight", 400)
                weight_class = variant.get("weight_class", 400)
                
                # Standard weight mapping
                standard_weights = {100: 100, 200: 200, 300: 300, 400: 400, 
                                   500: 500, 600: 600, 700: 700, 800: 800, 900: 900}
                
                if weight in standard_weights and weight_class == standard_weights[weight]:
                    if "weight_class" in variant:
                        del variant["weight_class"]
                        removed_fields += 1
        
        print(f"Removed {removed_fields} redundant metadata fields")
    
    def optimize_preview_data(self):
        """Optimize SVG preview data for better compression"""
        print("Optimizing preview data...")
        
        fonts = self.database.get("fonts", {})
        optimized_previews = 0
        total_savings = 0
        
        for family_name, font_data in fonts.items():
            preview = font_data.get("preview", {})
            if not preview:
                continue
            
            svg_compressed = preview.get("svg_compressed", "")
            if not svg_compressed:
                continue
            
            original_size = len(svg_compressed)
            
            # Try further compression techniques
            try:
                # Decode and re-encode with higher compression
                import base64
                import gzip
                
                compressed_data = base64.b64decode(svg_compressed)
                decompressed = gzip.decompress(compressed_data)
                
                # Re-compress with maximum compression
                recompressed = gzip.compress(decompressed, compresslevel=9)
                reencoded = base64.b64encode(recompressed).decode('ascii')
                
                if len(reencoded) < original_size:
                    preview["svg_compressed"] = reencoded
                    preview["compressed_size"] = len(reencoded)
                    savings = original_size - len(reencoded)
                    total_savings += savings
                    optimized_previews += 1
                    
            except Exception as e:
                print(f"Error optimizing preview for {family_name}: {e}")
        
        print(f"Optimized {optimized_previews} preview files, saved {total_savings} bytes")
    
    def deduplicate_urls(self):
        """Deduplicate similar download URLs using patterns"""
        print("Deduplicating URLs...")
        
        fonts = self.database.get("fonts", {})
        url_patterns = {}
        deduplicated_count = 0
        
        # Analyze URL patterns
        for family_name, font_data in fonts.items():
            variants = font_data.get("variants", [])
            
            for variant in variants:
                url = variant.get("download_url", "")
                if not url:
                    continue
                
                # Extract pattern (everything except the filename)
                base_url = "/".join(url.split("/")[:-1]) + "/"
                
                if base_url not in url_patterns:
                    url_patterns[base_url] = []
                url_patterns[base_url].append((family_name, variant))
        
        # Apply deduplication for families with common patterns
        for base_url, variants in url_patterns.items():
            if len(variants) > 1:
                # Store base URL in family data
                family_groups = {}
                for family_name, variant in variants:
                    if family_name not in family_groups:
                        family_groups[family_name] = []
                    family_groups[family_name].append(variant)
                
                for family_name, family_variants in family_groups.items():
                    if len(family_variants) > 1:
                        fonts[family_name]["base_url"] = base_url
                        for variant in family_variants:
                            # Store only filename instead of full URL
                            url = variant["download_url"]
                            filename = url.split("/")[-1]
                            variant["filename"] = filename
                            del variant["download_url"]
                            deduplicated_count += 1
        
        print(f"Deduplicated {deduplicated_count} URLs")
    
    def create_index_files(self):
        """Create optimized index files for different use cases"""
        print("Creating index files...")
        
        fonts = self.database.get("fonts", {})
        
        # 1. Family names only (for autocomplete)
        family_index = {
            "families": sorted(fonts.keys()),
            "count": len(fonts),
            "version": self.database.get("version", ""),
            "updated": self.database.get("updated", "")
        }
        
        with open("font-families-index.json", 'w', encoding='utf-8') as f:
            json.dump(family_index, f, separators=(',', ':'))
        
        # 2. Categories index
        categories = {}
        for family_name, font_data in fonts.items():
            category = font_data.get("category", "sans-serif")
            if category not in categories:
                categories[category] = []
            categories[category].append(family_name)
        
        category_index = {
            "categories": {cat: sorted(families) for cat, families in categories.items()},
            "version": self.database.get("version", ""),
            "updated": self.database.get("updated", "")
        }
        
        with open("font-categories-index.json", 'w', encoding='utf-8') as f:
            json.dump(category_index, f, separators=(',', ':'))
        
        # 3. Popular fonts (families with most variants)
        popular_fonts = sorted(
            [(name, len(data.get("variants", []))) for name, data in fonts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:100]  # Top 100
        
        popular_index = {
            "popular": [{"family": name, "variants": count} for name, count in popular_fonts],
            "version": self.database.get("version", ""),
            "updated": self.database.get("updated", "")
        }
        
        with open("font-popular-index.json", 'w', encoding='utf-8') as f:
            json.dump(popular_index, f, separators=(',', ':'))
        
        print("Created index files: families, categories, popular")
    
    def validate_optimization(self):
        """Validate that optimization didn't break data integrity"""
        print("Validating optimization...")
        
        fonts = self.database.get("fonts", {})
        issues = []
        
        for family_name, font_data in fonts.items():
            # Check required fields
            if "category" not in font_data:
                issues.append(f"{family_name}: Missing category")
            
            if "variants" not in font_data or not font_data["variants"]:
                issues.append(f"{family_name}: No variants")
                continue
            
            # Check variants
            for i, variant in enumerate(font_data["variants"]):
                if "weight" not in variant:
                    issues.append(f"{family_name} variant {i}: Missing weight")
                
                if "style" not in variant:
                    issues.append(f"{family_name} variant {i}: Missing style")
                
                # Check URL/filename consistency
                has_url = "download_url" in variant
                has_filename = "filename" in variant
                has_base_url = "base_url" in font_data
                
                if not has_url and not (has_filename and has_base_url):
                    issues.append(f"{family_name} variant {i}: Missing download info")
        
        if issues:
            print(f"Found {len(issues)} validation issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
            return False
        else:
            print("Validation passed - no issues found")
            return True
    
    def save_optimized_database(self):
        """Save the optimized database"""
        print("Saving optimized database...")
        
        # Update metadata
        self.database["optimized"] = True
        self.database["optimization_date"] = datetime.now().isoformat() + "Z"
        
        # Save optimized version
        with open(self.optimized_file, 'w', encoding='utf-8') as f:
            json.dump(self.database, f, separators=(',', ':'), ensure_ascii=False)
        
        # Update the original database file with optimized version
        with open(self.database_file, 'w', encoding='utf-8') as f:
            json.dump(self.database, f, separators=(',', ':'), ensure_ascii=False)
        
        # Create compressed version from optimized database
        with open(self.database_file, 'rb') as f_in:
            with gzip.open(self.compressed_file, 'wb', compresslevel=9) as f_out:
                f_out.write(f_in.read())
        
        # Calculate sizes and savings
        original_size = Path(self.database_file).stat().st_size
        optimized_size = Path(self.optimized_file).stat().st_size
        compressed_size = Path(self.compressed_file).stat().st_size
        
        print(f"Database optimization completed:")
        print(f"  Database: {original_size / 1024:.1f} KB")
        print(f"  Optimized copy: {optimized_size / 1024:.1f} KB")
        print(f"  Compressed: {compressed_size / 1024:.1f} KB ({(1 - compressed_size/original_size)*100:.1f}% reduction)")
        
        # Create checksums
        self.create_checksums()
    
    def create_checksums(self):
        """Create checksum files for integrity verification"""
        files_to_hash = [
            self.optimized_file,
            self.compressed_file,
            "font-families-index.json",
            "font-categories-index.json", 
            "font-popular-index.json"
        ]
        
        checksums = {}
        
        for filename in files_to_hash:
            if Path(filename).exists():
                with open(filename, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    checksums[filename] = file_hash
        
        with open("checksums.json", 'w') as f:
            json.dump(checksums, f, indent=2)
        
        print(f"Created checksums for {len(checksums)} files")
    
    def optimize(self):
        """Run complete optimization process"""
        print("Starting database optimization...")
        
        # Optimization steps
        self.remove_redundant_metadata()
        self.optimize_preview_data()
        self.deduplicate_urls()
        
        # Validation
        if not self.validate_optimization():
            print("Optimization failed validation!")
            return False
        
        # Create optimized files
        self.create_index_files()
        self.save_optimized_database()
        
        print("Database optimization completed successfully!")
        return True


def main():
    """Main execution function"""
    if not Path("font-database.json").exists():
        print("Error: font-database.json not found!")
        print("Run generate_metadata.py and generate_svg_previews.py first.")
        return 1
    
    optimizer = DatabaseOptimizer()
    success = optimizer.optimize()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
