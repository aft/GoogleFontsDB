#!/usr/bin/env python3
"""
Output Validation Script

Validates the generated font database and associated files:
- JSON schema validation
- Data integrity checks
- File consistency verification
- URL validation
- Preview data validation
- Performance benchmarks

Cem Baspinar, 2025, MIT License.
"""

import os
import json
import gzip
import base64
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse


class DatabaseValidator:
    def __init__(self):
        self.required_files = [
            "font-database.json",
            "font-families-index.json",
            "font-categories-index.json",
            "font-popular-index.json",
            "stats.json"
        ]
        
        self.optional_files = [
            "font-database-optimized.json",
            "font-database.json.gz",
            "checksums.json"
        ]
        
        self.errors = []
        self.warnings = []
        self.info = []
        
    def log_error(self, message):
        """Log validation error"""
        self.errors.append(message)
        print(f"ERROR: {message}")
    
    def log_warning(self, message):
        """Log validation warning"""
        self.warnings.append(message)
        print(f"WARNING: {message}")
    
    def log_info(self, message):
        """Log validation info"""
        self.info.append(message)
        print(f"INFO: {message}")
    
    def validate_file_existence(self):
        """Validate that required files exist"""
        print("Validating file existence...")
        
        for filename in self.required_files:
            if not Path(filename).exists():
                self.log_error(f"Required file missing: {filename}")
            else:
                self.log_info(f"Required file found: {filename}")
        
        for filename in self.optional_files:
            if Path(filename).exists():
                self.log_info(f"Optional file found: {filename}")
    
    def validate_json_structure(self):
        """Validate JSON file structure and syntax"""
        print("Validating JSON structure...")
        
        json_files = [f for f in self.required_files + self.optional_files if f.endswith('.json')]
        
        for filename in json_files:
            if not Path(filename).exists():
                continue
            
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Basic structure validation
                if filename == "font-database.json":
                    self.validate_main_database_structure(data)
                elif filename == "font-families-index.json":
                    self.validate_families_index_structure(data)
                elif filename == "font-categories-index.json":
                    self.validate_categories_index_structure(data)
                elif filename == "stats.json":
                    self.validate_stats_structure(data)
                
                self.log_info(f"JSON structure valid: {filename}")
                
            except json.JSONDecodeError as e:
                self.log_error(f"Invalid JSON in {filename}: {e}")
            except Exception as e:
                self.log_error(f"Error validating {filename}: {e}")
    
    def validate_main_database_structure(self, data):
        """Validate main database structure"""
        required_fields = ["version", "updated", "total_families", "fonts"]
        
        for field in required_fields:
            if field not in data:
                self.log_error(f"Missing required field in database: {field}")
        
        # Validate fonts structure
        fonts = data.get("fonts", {})
        if not isinstance(fonts, dict):
            self.log_error("fonts field must be a dictionary")
            return
        
        sample_size = min(10, len(fonts))  # Validate sample of fonts
        font_items = list(fonts.items())[:sample_size]
        
        for family_name, font_data in font_items:
            self.validate_font_entry(family_name, font_data)
    
    def validate_font_entry(self, family_name, font_data):
        """Validate individual font entry"""
        required_fields = ["category", "variants"]
        
        for field in required_fields:
            if field not in font_data:
                self.log_error(f"Font {family_name} missing required field: {field}")
        
        # Validate variants
        variants = font_data.get("variants", [])
        if not isinstance(variants, list) or not variants:
            self.log_error(f"Font {family_name} has no variants")
            return
        
        for i, variant in enumerate(variants):
            self.validate_variant(family_name, i, variant, font_data)
    
    def validate_variant(self, family_name, variant_index, variant, font_data):
        """Validate individual variant"""
        required_fields = ["weight", "style"]
        
        for field in required_fields:
            if field not in variant:
                self.log_error(f"Font {family_name} variant {variant_index} missing: {field}")
        
        # Validate weight
        weight = variant.get("weight")
        if weight is not None and (not isinstance(weight, int) or weight < 100 or weight > 900):
            self.log_warning(f"Font {family_name} variant {variant_index} has unusual weight: {weight}")
        
        # Validate style
        style = variant.get("style", "")
        valid_styles = {"normal", "italic", "oblique"}
        if style not in valid_styles:
            self.log_warning(f"Font {family_name} variant {variant_index} has unusual style: {style}")
        
        # Validate download URL or filename
        has_url = "download_url" in variant
        has_filename = "filename" in variant
        has_base_url = "base_url" in font_data
        
        if not has_url and not (has_filename and has_base_url):
            self.log_error(f"Font {family_name} variant {variant_index} missing download information")
        
        # Validate URL format if present
        if has_url:
            url = variant["download_url"]
            if not url.startswith("https://"):
                self.log_warning(f"Font {family_name} variant {variant_index} URL not HTTPS: {url}")
    
    def validate_families_index_structure(self, data):
        """Validate families index structure"""
        required_fields = ["families", "count", "version"]
        
        for field in required_fields:
            if field not in data:
                self.log_error(f"Missing required field in families index: {field}")
        
        families = data.get("families", [])
        if not isinstance(families, list):
            self.log_error("families field must be a list")
        
        count = data.get("count", 0)
        if len(families) != count:
            self.log_warning(f"Family count mismatch: listed {len(families)}, reported {count}")
    
    def validate_categories_index_structure(self, data):
        """Validate categories index structure"""
        required_fields = ["categories", "version"]
        
        for field in required_fields:
            if field not in data:
                self.log_error(f"Missing required field in categories index: {field}")
        
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            self.log_error("categories field must be a dictionary")
    
    def validate_stats_structure(self, data):
        """Validate statistics structure"""
        expected_sections = ["basic", "file_sizes", "previews", "licenses", "popular", "quality", "database"]
        
        for section in expected_sections:
            if section not in data:
                self.log_warning(f"Missing statistics section: {section}")
    
    def validate_preview_data(self):
        """Validate SVG preview data"""
        print("Validating preview data...")
        
        if not Path("font-database.json").exists():
            return
        
        with open("font-database.json", 'r', encoding='utf-8') as f:
            database = json.load(f)
        
        fonts = database.get("fonts", {})
        preview_errors = 0
        preview_count = 0
        
        # Sample validation (check first 20 fonts with previews)
        sample_count = 0
        for family_name, font_data in fonts.items():
            preview = font_data.get("preview", {})
            if not preview:
                continue
            
            preview_count += 1
            sample_count += 1
            if sample_count > 20:
                break
            
            # Validate compressed SVG data
            svg_compressed = preview.get("svg_compressed", "")
            if not svg_compressed:
                self.log_warning(f"Font {family_name} has empty preview data")
                preview_errors += 1
                continue
            
            try:
                # Test decompression
                compressed_data = base64.b64decode(svg_compressed)
                decompressed = gzip.decompress(compressed_data)
                svg_content = decompressed.decode('utf-8')
                
                # Basic SVG validation
                if not svg_content.strip().startswith('<svg'):
                    self.log_warning(f"Font {family_name} preview doesn't start with <svg")
                    preview_errors += 1
                
                if '</svg>' not in svg_content:
                    self.log_warning(f"Font {family_name} preview missing closing </svg>")
                    preview_errors += 1
                    
            except Exception as e:
                self.log_error(f"Font {family_name} preview decompression failed: {e}")
                preview_errors += 1
        
        if preview_count > 0:
            error_rate = (preview_errors / preview_count) * 100
            self.log_info(f"Preview validation: {preview_count} previews checked, {preview_errors} errors ({error_rate:.1f}% error rate)")
            
            if error_rate > 10:
                self.log_warning(f"High preview error rate: {error_rate:.1f}%")
    
    def validate_checksums(self):
        """Validate file checksums if available"""
        print("Validating checksums...")
        
        if not Path("checksums.json").exists():
            self.log_info("No checksums file found - skipping checksum validation")
            return
        
        with open("checksums.json", 'r') as f:
            expected_checksums = json.load(f)
        
        checksum_errors = 0
        
        for filename, expected_hash in expected_checksums.items():
            if not Path(filename).exists():
                self.log_error(f"Checksum file missing: {filename}")
                checksum_errors += 1
                continue
            
            # Calculate actual hash
            with open(filename, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            if actual_hash != expected_hash:
                self.log_error(f"Checksum mismatch for {filename}")
                checksum_errors += 1
            else:
                self.log_info(f"Checksum valid: {filename}")
        
        if checksum_errors == 0:
            self.log_info("All checksums validated successfully")
    
    def validate_compression_integrity(self):
        """Validate compressed file integrity"""
        print("Validating compressed files...")
        
        if Path("font-database.json.gz").exists():
            try:
                with gzip.open("font-database.json.gz", 'rt', encoding='utf-8') as f:
                    compressed_data = json.load(f)
                
                # Compare with original
                if Path("font-database.json").exists():
                    with open("font-database.json", 'r', encoding='utf-8') as f:
                        original_data = json.load(f)
                    
                    if compressed_data != original_data:
                        self.log_error("Compressed database doesn't match original")
                    else:
                        self.log_info("Compressed database integrity verified")
                else:
                    self.log_info("Compressed database readable")
                    
            except Exception as e:
                self.log_error(f"Error reading compressed database: {e}")
    
    def validate_performance_metrics(self):
        """Validate performance characteristics"""
        print("Validating performance metrics...")
        
        # File size checks
        file_sizes = {}
        for filename in self.required_files + self.optional_files:
            if Path(filename).exists():
                size = Path(filename).stat().st_size
                file_sizes[filename] = size
        
        # Main database size check
        main_db_size = file_sizes.get("font-database.json", 0)
        if main_db_size > 50 * 1024 * 1024:  # 50MB
            self.log_warning(f"Main database very large: {main_db_size / (1024*1024):.1f}MB")
        elif main_db_size > 10 * 1024 * 1024:  # 10MB
            self.log_info(f"Main database size: {main_db_size / (1024*1024):.1f}MB")
        
        # Compression ratio check
        if "font-database.json.gz" in file_sizes:
            compressed_size = file_sizes["font-database.json.gz"]
            compression_ratio = compressed_size / main_db_size if main_db_size > 0 else 1
            
            if compression_ratio > 0.8:
                self.log_warning(f"Poor compression ratio: {compression_ratio:.2f}")
            else:
                self.log_info(f"Good compression ratio: {compression_ratio:.2f}")
    
    def generate_validation_report(self):
        """Generate validation report"""
        print("\n=== Validation Report ===")
        
        report = {
            "validation_date": datetime.now().isoformat() + "Z",
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "info_messages": len(self.info),
            "overall_status": "PASS" if len(self.errors) == 0 else "FAIL",
            "details": {
                "errors": self.errors,
                "warnings": self.warnings,
                "info": self.info
            }
        }
        
        # Save report
        with open("validation-report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Info messages: {len(self.info)}")
        print(f"Overall status: {report['overall_status']}")
        
        if self.errors:
            print("\nErrors found:")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more errors")
        
        print(f"\nValidation report saved to validation-report.json")
        
        return len(self.errors) == 0
    
    def validate_all(self):
        """Run complete validation suite"""
        print("Starting comprehensive validation...")
        
        self.validate_file_existence()
        self.validate_json_structure()
        self.validate_preview_data()
        self.validate_checksums()
        self.validate_compression_integrity()
        self.validate_performance_metrics()
        
        success = self.generate_validation_report()
        
        if success:
            print("Validation completed successfully - no errors found!")
        else:
            print("Validation completed with errors - see report for details")
        
        return success


def main():
    """Main execution function"""
    validator = DatabaseValidator()
    success = validator.validate_all()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
