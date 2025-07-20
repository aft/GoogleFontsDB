#!/usr/bin/env python3
"""
Statistics Generation Script

Generates comprehensive statistics about the Google Fonts database:
- Font family and variant counts
- Category distribution
- File size analysis
- Preview data statistics
- Quality metrics
- Trends and insights

Cem Baspinar, 2025, MIT License.
"""

import os
import json
import statistics
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


class FontStatisticsGenerator:
    def __init__(self, database_file="font-database.json"):
        self.database_file = database_file
        self.stats_file = "stats.json"
        
        # Load database
        with open(database_file, 'r', encoding='utf-8') as f:
            self.database = json.load(f)
        
        self.fonts = self.database.get("fonts", {})
        self.stats = {
            "generated": datetime.now().isoformat() + "Z",
            "database_version": self.database.get("version", "unknown"),
            "database_updated": self.database.get("updated", "unknown")
        }
    
    def generate_basic_stats(self):
        """Generate basic font statistics"""
        print("Generating basic statistics...")
        
        total_families = len(self.fonts)
        total_variants = sum(len(font_data.get("variants", [])) for font_data in self.fonts.values())
        
        # Category distribution
        categories = Counter()
        for font_data in self.fonts.values():
            category = font_data.get("category", "unknown")
            categories[category] += 1
        
        # Weight distribution
        weights = Counter()
        styles = Counter()
        for font_data in self.fonts.values():
            for variant in font_data.get("variants", []):
                weight = variant.get("weight", 400)
                style = variant.get("style", "normal")
                weights[weight] += 1
                styles[style] += 1
        
        self.stats["basic"] = {
            "total_families": total_families,
            "total_variants": total_variants,
            "avg_variants_per_family": round(total_variants / total_families if total_families > 0 else 0, 2),
            "categories": dict(categories.most_common()),
            "weights": dict(weights.most_common()),
            "styles": dict(styles.most_common())
        }
        
        print(f"Processed {total_families} families with {total_variants} variants")
    
    def analyze_file_sizes(self):
        """Analyze font file sizes"""
        print("Analyzing file sizes...")
        
        file_sizes = []
        size_by_category = defaultdict(list)
        size_by_weight = defaultdict(list)
        
        for family_name, font_data in self.fonts.items():
            category = font_data.get("category", "unknown")
            
            # Check for average file size (optimized databases)
            avg_size = font_data.get("avg_file_size")
            if avg_size:
                file_sizes.append(avg_size)
                size_by_category[category].append(avg_size)
                continue
            
            # Individual variant sizes
            for variant in font_data.get("variants", []):
                size = variant.get("file_size")
                if size:
                    file_sizes.append(size)
                    weight = variant.get("weight", 400)
                    size_by_category[category].append(size)
                    size_by_weight[weight].append(size)
        
        if file_sizes:
            # Overall statistics
            size_stats = {
                "total_files": len(file_sizes),
                "total_size_mb": round(sum(file_sizes) / (1024 * 1024), 2),
                "avg_size_kb": round(statistics.mean(file_sizes) / 1024, 2),
                "median_size_kb": round(statistics.median(file_sizes) / 1024, 2),
                "min_size_kb": round(min(file_sizes) / 1024, 2),
                "max_size_kb": round(max(file_sizes) / 1024, 2),
                "std_dev_kb": round(statistics.stdev(file_sizes) / 1024, 2) if len(file_sizes) > 1 else 0
            }
            
            # Category breakdown
            category_stats = {}
            for category, sizes in size_by_category.items():
                if sizes:
                    category_stats[category] = {
                        "count": len(sizes),
                        "avg_size_kb": round(statistics.mean(sizes) / 1024, 2),
                        "total_size_mb": round(sum(sizes) / (1024 * 1024), 2)
                    }
            
            # Weight breakdown
            weight_stats = {}
            for weight, sizes in size_by_weight.items():
                if sizes and len(sizes) > 1:
                    weight_stats[str(weight)] = {
                        "count": len(sizes),
                        "avg_size_kb": round(statistics.mean(sizes) / 1024, 2)
                    }
            
            self.stats["file_sizes"] = {
                "overall": size_stats,
                "by_category": category_stats,
                "by_weight": weight_stats
            }
        else:
            self.stats["file_sizes"] = {"error": "No file size data available"}
    
    def analyze_preview_data(self):
        """Analyze SVG preview statistics"""
        print("Analyzing preview data...")
        
        preview_stats = {
            "families_with_previews": 0,
            "total_compressed_size": 0,
            "preview_sizes": [],
            "compression_ratios": []
        }
        
        for family_name, font_data in self.fonts.items():
            preview = font_data.get("preview", {})
            if not preview:
                continue
            
            preview_stats["families_with_previews"] += 1
            
            compressed_size = preview.get("compressed_size", 0)
            original_size = preview.get("original_size", 0)
            
            if compressed_size > 0:
                preview_stats["total_compressed_size"] += compressed_size
                preview_stats["preview_sizes"].append(compressed_size)
                
                if original_size > 0:
                    ratio = compressed_size / original_size
                    preview_stats["compression_ratios"].append(ratio)
        
        # Calculate statistics
        if preview_stats["preview_sizes"]:
            sizes = preview_stats["preview_sizes"]
            preview_stats.update({
                "avg_preview_size": round(statistics.mean(sizes), 0),
                "median_preview_size": round(statistics.median(sizes), 0),
                "min_preview_size": min(sizes),
                "max_preview_size": max(sizes),
                "total_preview_size_mb": round(preview_stats["total_compressed_size"] / (1024 * 1024), 2)
            })
        
        if preview_stats["compression_ratios"]:
            ratios = preview_stats["compression_ratios"]
            preview_stats.update({
                "avg_compression_ratio": round(statistics.mean(ratios), 3),
                "median_compression_ratio": round(statistics.median(ratios), 3),
                "best_compression": round(min(ratios), 3),
                "worst_compression": round(max(ratios), 3)
            })
        
        # Clean up temporary lists
        del preview_stats["preview_sizes"]
        del preview_stats["compression_ratios"]
        
        self.stats["previews"] = preview_stats
    
    def analyze_license_distribution(self):
        """Analyze license distribution"""
        print("Analyzing license distribution...")
        
        licenses = Counter()
        license_by_category = defaultdict(Counter)
        
        for family_name, font_data in self.fonts.items():
            license_info = font_data.get("license", {})
            license_type = license_info.get("type", "unknown")
            category = font_data.get("category", "unknown")
            
            licenses[license_type] += 1
            license_by_category[category][license_type] += 1
        
        self.stats["licenses"] = {
            "distribution": dict(licenses.most_common()),
            "by_category": {cat: dict(counter.most_common()) for cat, counter in license_by_category.items()}
        }
    
    def identify_popular_fonts(self):
        """Identify popular fonts based on variant count"""
        print("Identifying popular fonts...")
        
        # Fonts with most variants
        variant_counts = []
        for family_name, font_data in self.fonts.items():
            variant_count = len(font_data.get("variants", []))
            variant_counts.append((family_name, variant_count))
        
        # Sort by variant count
        variant_counts.sort(key=lambda x: x[1], reverse=True)
        
        # Top families
        top_families = variant_counts[:20]
        
        # Families with many weights (indicating professional fonts)
        weights_per_family = []
        for family_name, font_data in self.fonts.items():
            weights = set()
            for variant in font_data.get("variants", []):
                weights.add(variant.get("weight", 400))
            weights_per_family.append((family_name, len(weights)))
        
        weights_per_family.sort(key=lambda x: x[1], reverse=True)
        professional_fonts = weights_per_family[:15]
        
        self.stats["popular"] = {
            "most_variants": [{"family": name, "variants": count} for name, count in top_families],
            "most_weights": [{"family": name, "weights": count} for name, count in professional_fonts],
            "single_variant_families": len([x for x in variant_counts if x[1] == 1]),
            "multi_variant_families": len([x for x in variant_counts if x[1] > 1])
        }
    
    def calculate_quality_metrics(self):
        """Calculate database quality metrics"""
        print("Calculating quality metrics...")
        
        quality = {
            "completeness": {},
            "consistency": {},
            "coverage": {}
        }
        
        # Completeness metrics
        families_with_previews = len([f for f in self.fonts.values() if f.get("preview")])
        families_with_license = len([f for f in self.fonts.values() if f.get("license")])
        variants_with_sizes = 0
        total_variants = 0
        
        for font_data in self.fonts.values():
            for variant in font_data.get("variants", []):
                total_variants += 1
                if variant.get("file_size") or font_data.get("avg_file_size"):
                    variants_with_sizes += 1
        
        quality["completeness"] = {
            "preview_coverage": round(families_with_previews / len(self.fonts) * 100, 1) if self.fonts else 0,
            "license_coverage": round(families_with_license / len(self.fonts) * 100, 1) if self.fonts else 0,
            "size_data_coverage": round(variants_with_sizes / total_variants * 100, 1) if total_variants else 0
        }
        
        # Consistency metrics
        missing_categories = len([f for f in self.fonts.values() if not f.get("category")])
        invalid_weights = 0
        invalid_styles = 0
        
        valid_weights = {100, 200, 300, 400, 500, 600, 700, 800, 900}
        valid_styles = {"normal", "italic", "oblique"}
        
        for font_data in self.fonts.values():
            for variant in font_data.get("variants", []):
                weight = variant.get("weight", 400)
                style = variant.get("style", "normal")
                
                if weight not in valid_weights:
                    invalid_weights += 1
                if style not in valid_styles:
                    invalid_styles += 1
        
        quality["consistency"] = {
            "missing_categories": missing_categories,
            "invalid_weights": invalid_weights,
            "invalid_styles": invalid_styles,
            "consistency_score": round((1 - (missing_categories + invalid_weights + invalid_styles) / (len(self.fonts) + total_variants)) * 100, 1)
        }
        
        # Coverage metrics
        category_counts = Counter(font_data.get("category", "unknown") for font_data in self.fonts.values())
        weight_counts = Counter()
        for font_data in self.fonts.values():
            for variant in font_data.get("variants", []):
                weight_counts[variant.get("weight", 400)] += 1
        
        quality["coverage"] = {
            "categories_covered": len(category_counts),
            "weights_covered": len(weight_counts),
            "most_common_category": category_counts.most_common(1)[0] if category_counts else None,
            "most_common_weight": weight_counts.most_common(1)[0] if weight_counts else None
        }
        
        self.stats["quality"] = quality
    
    def generate_database_metadata(self):
        """Generate metadata about the database itself"""
        print("Generating database metadata...")
        
        db_file_size = Path(self.database_file).stat().st_size
        
        # Check for optimized files
        optimized_files = {}
        for filename in ["font-database-optimized.json", "font-database.json.gz"]:
            if Path(filename).exists():
                optimized_files[filename] = Path(filename).stat().st_size
        
        # Index files
        index_files = {}
        for filename in ["font-families-index.json", "font-categories-index.json", "font-popular-index.json"]:
            if Path(filename).exists():
                index_files[filename] = Path(filename).stat().st_size
        
        metadata = {
            "original_database_size_kb": round(db_file_size / 1024, 2),
            "optimized_files": {name: round(size / 1024, 2) for name, size in optimized_files.items()},
            "index_files": {name: round(size / 1024, 2) for name, size in index_files.items()},
            "database_version": self.database.get("version", "unknown"),
            "last_updated": self.database.get("updated", "unknown"),
            "optimization_applied": self.database.get("optimized", False)
        }
        
        # Calculate total distribution size
        total_size = db_file_size + sum(optimized_files.values()) + sum(index_files.values())
        metadata["total_distribution_size_kb"] = round(total_size / 1024, 2)
        
        self.stats["database"] = metadata
    
    def save_statistics(self):
        """Save statistics to JSON file"""
        print(f"Saving statistics to {self.stats_file}...")
        
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        # Print summary
        basic = self.stats.get("basic", {})
        database = self.stats.get("database", {})
        quality = self.stats.get("quality", {})
        
        print("\n=== Font Database Statistics Summary ===")
        print(f"Font families: {basic.get('total_families', 0):,}")
        print(f"Font variants: {basic.get('total_variants', 0):,}")
        print(f"Database size: {database.get('original_database_size_kb', 0):.1f} KB")
        print(f"Preview coverage: {quality.get('completeness', {}).get('preview_coverage', 0):.1f}%")
        print(f"Quality score: {quality.get('consistency', {}).get('consistency_score', 0):.1f}%")
        
        if basic.get("categories"):
            print(f"Top category: {max(basic['categories'], key=basic['categories'].get)} ({basic['categories'][max(basic['categories'], key=basic['categories'].get)]} families)")
        
        print(f"Statistics saved to {self.stats_file}")
    
    def generate_all_statistics(self):
        """Generate complete statistics report"""
        print("Starting comprehensive statistics generation...")
        
        self.generate_basic_stats()
        self.analyze_file_sizes()
        self.analyze_preview_data()
        self.analyze_license_distribution()
        self.identify_popular_fonts()
        self.calculate_quality_metrics()
        self.generate_database_metadata()
        self.save_statistics()
        
        print("Statistics generation completed successfully!")


def main():
    """Main execution function"""
    if not Path("font-database.json").exists():
        print("Error: font-database.json not found!")
        print("Run the font processing pipeline first.")
        return 1
    
    generator = FontStatisticsGenerator()
    generator.generate_all_statistics()
    
    return 0


if __name__ == "__main__":
    exit(main())
