#!/usr/bin/env python3
"""
Changelog Generation Script

Compares the current font database with the previous version to generate
a detailed changelog of new fonts, updated fonts, and removed fonts.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class ChangelogGenerator:
    def __init__(self, current_db_file="font-database.json", changelog_file="CHANGELOG.md"):
        self.current_db_file = current_db_file
        self.changelog_file = changelog_file
        self.previous_db_url = "https://raw.githubusercontent.com/aft/GoogleFontsDB/main/font-database.json"
        
        # Load current database
        with open(current_db_file, 'r', encoding='utf-8') as f:
            self.current_db = json.load(f)
            
        self.previous_db = None
        self.changes = {
            "new_fonts": {},
            "updated_fonts": {},
            "removed_fonts": {},
            "new_variants": defaultdict(list),
            "removed_variants": defaultdict(list)
        }
    
    def fetch_previous_database(self):
        """Fetch the previous version of the database from GitHub"""
        try:
            print("Fetching previous database version...")
            response = requests.get(self.previous_db_url, timeout=30)
            response.raise_for_status()
            self.previous_db = response.json()
            print(f"Previous database loaded: {len(self.previous_db.get('fonts', {}))} families")
            return True
        except Exception as e:
            print(f"Could not fetch previous database: {e}")
            print("This might be the first run or the repository is not yet published")
            return False
    
    def compare_databases(self):
        """Compare current and previous databases to detect changes"""
        if not self.previous_db:
            print("No previous database to compare - treating all fonts as new")
            self.changes["new_fonts"] = self.current_db.get("fonts", {})
            return
        
        current_fonts = self.current_db.get("fonts", {})
        previous_fonts = self.previous_db.get("fonts", {})
        
        print("Comparing databases for changes...")
        
        # Find new fonts
        for family_name, font_data in current_fonts.items():
            if family_name not in previous_fonts:
                self.changes["new_fonts"][family_name] = font_data
            else:
                # Check for new variants
                current_variants = font_data.get("variants", [])
                previous_variants = previous_fonts[family_name].get("variants", [])
                
                # Compare variants by weight and style
                previous_variant_keys = {(v.get("weight"), v.get("style")) for v in previous_variants}
                
                for variant in current_variants:
                    variant_key = (variant.get("weight"), variant.get("style"))
                    if variant_key not in previous_variant_keys:
                        self.changes["new_variants"][family_name].append(variant)
                
                # Check if font was updated (different number of variants or preview added)
                if len(current_variants) != len(previous_variants):
                    self.changes["updated_fonts"][family_name] = {
                        "previous_variants": len(previous_variants),
                        "current_variants": len(current_variants)
                    }
                elif "preview" in font_data and "preview" not in previous_fonts[family_name]:
                    self.changes["updated_fonts"][family_name] = {
                        "change": "preview_added"
                    }
        
        # Find removed fonts
        for family_name in previous_fonts:
            if family_name not in current_fonts:
                self.changes["removed_fonts"][family_name] = previous_fonts[family_name]
        
        print(f"Changes detected:")
        print(f"  New fonts: {len(self.changes['new_fonts'])}")
        print(f"  Updated fonts: {len(self.changes['updated_fonts'])}")
        print(f"  Removed fonts: {len(self.changes['removed_fonts'])}")
        print(f"  Fonts with new variants: {len(self.changes['new_variants'])}")
    
    def generate_release_changelog(self):
        """Generate changelog content for release notes"""
        changelog_lines = []
        
        # Summary
        total_current = len(self.current_db.get("fonts", {}))
        total_previous = len(self.previous_db.get("fonts", {})) if self.previous_db else 0
        net_change = total_current - total_previous
        
        changelog_lines.append("## 📈 Database Changes")
        changelog_lines.append("")
        changelog_lines.append(f"**Total font families:** {total_current:,} ({net_change:+d} from previous version)")
        changelog_lines.append("")
        
        # New fonts
        if self.changes["new_fonts"]:
            changelog_lines.append(f"### ✨ New Fonts ({len(self.changes['new_fonts'])})")
            changelog_lines.append("")
            
            # Group by category
            by_category = defaultdict(list)
            for family_name, font_data in self.changes["new_fonts"].items():
                category = font_data.get("category", "unknown")
                variant_count = len(font_data.get("variants", []))
                by_category[category].append(f"**{family_name}** ({variant_count} variants)")
            
            for category, fonts in sorted(by_category.items()):
                changelog_lines.append(f"**{category.title()}:**")
                for font in sorted(fonts)[:10]:  # Limit to 10 per category
                    changelog_lines.append(f"- {font}")
                if len(fonts) > 10:
                    changelog_lines.append(f"- ... and {len(fonts) - 10} more {category} fonts")
                changelog_lines.append("")
        
        # Updated fonts
        if self.changes["updated_fonts"]:
            changelog_lines.append(f"### 🔄 Updated Fonts ({len(self.changes['updated_fonts'])})")
            changelog_lines.append("")
            
            for family_name, update_info in sorted(self.changes["updated_fonts"].items()):
                if "previous_variants" in update_info:
                    prev_count = update_info["previous_variants"]
                    curr_count = update_info["current_variants"]
                    change = curr_count - prev_count
                    changelog_lines.append(f"- **{family_name}**: {prev_count} → {curr_count} variants ({change:+d})")
                elif update_info.get("change") == "preview_added":
                    changelog_lines.append(f"- **{family_name}**: Preview added")
            
            changelog_lines.append("")
        
        # New variants
        if self.changes["new_variants"]:
            new_variant_families = [f for f, variants in self.changes["new_variants"].items() if variants]
            if new_variant_families:
                changelog_lines.append(f"### 🆕 New Variants ({len(new_variant_families)} families)")
                changelog_lines.append("")
                
                for family_name in sorted(new_variant_families)[:10]:  # Show first 10
                    variants = self.changes["new_variants"][family_name]
                    variant_desc = []
                    for v in variants:
                        weight = v.get("weight", 400)
                        style = v.get("style", "normal")
                        variant_desc.append(f"{weight} {style}")
                    changelog_lines.append(f"- **{family_name}**: {', '.join(variant_desc)}")
                
                if len(new_variant_families) > 10:
                    changelog_lines.append(f"- ... and {len(new_variant_families) - 10} more families with new variants")
                
                changelog_lines.append("")
        
        # Removed fonts
        if self.changes["removed_fonts"]:
            changelog_lines.append(f"### ❌ Removed Fonts ({len(self.changes['removed_fonts'])})")
            changelog_lines.append("")
            
            for family_name in sorted(self.changes["removed_fonts"].keys())[:20]:  # Show first 20
                changelog_lines.append(f"- {family_name}")
            
            if len(self.changes["removed_fonts"]) > 20:
                changelog_lines.append(f"- ... and {len(self.changes['removed_fonts']) - 20} more")
            
            changelog_lines.append("")
        
        # If no changes
        if not any(self.changes.values()):
            changelog_lines.append("### 📝 No Changes")
            changelog_lines.append("")
            changelog_lines.append("No new, updated, or removed fonts in this release.")
            changelog_lines.append("")
        
        return "\n".join(changelog_lines)
    
    def save_changelog_file(self):
        """Save a complete changelog file"""
        current_version = self.current_db.get("version", "unknown")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        changelog_content = []
        changelog_content.append("# Google Fonts Database Changelog")
        changelog_content.append("")
        changelog_content.append("All notable changes to the Google Fonts database will be documented in this file.")
        changelog_content.append("")
        
        # Current version
        changelog_content.append(f"## [{current_version}] - {current_date}")
        changelog_content.append("")
        changelog_content.append(self.generate_release_changelog())
        
        # Load existing changelog if it exists
        if Path(self.changelog_file).exists():
            with open(self.changelog_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Find where to insert the new version (after the header)
            lines = existing_content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('## [') and current_version not in line:
                    header_end = i
                    break
            
            if header_end > 0:
                # Insert new version before existing versions
                existing_versions = '\n'.join(lines[header_end:])
                changelog_content.append("---")
                changelog_content.append("")
                changelog_content.append(existing_versions)
        
        with open(self.changelog_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(changelog_content))
        
        print(f"Changelog saved to {self.changelog_file}")
    
    def generate_changelog(self):
        """Generate complete changelog"""
        print("Starting changelog generation...")
        
        has_previous = self.fetch_previous_database()
        self.compare_databases()
        
        # Generate release changelog for GitHub release
        release_changelog = self.generate_release_changelog()
        
        # Save to file for GitHub release
        with open("release-changelog.md", 'w', encoding='utf-8') as f:
            f.write(release_changelog)
        
        # Save complete changelog file
        self.save_changelog_file()
        
        print("Changelog generation completed!")
        return release_changelog


def main():
    """Main execution function"""
    if not Path("font-database.json").exists():
        print("Error: font-database.json not found!")
        return 1
    
    generator = ChangelogGenerator()
    generator.generate_changelog()
    
    return 0


if __name__ == "__main__":
    exit(main())