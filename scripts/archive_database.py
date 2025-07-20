#!/usr/bin/env python3
"""
Database Archive Management Script

Archives the current database to date-based folders before generating new versions.
Maintains historical versions organized by year/month structure.
Prevents duplicate archives for the same month.

Cem Baspinar, 2025, MIT License.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime


class DatabaseArchiver:
    def __init__(self):
        self.main_files = [
            "font-database.json",
            "font-database-optimized.json", 
            "font-database.json.gz",
            "font-families-index.json",
            "font-categories-index.json",
            "font-popular-index.json",
            "stats.json",
            "checksums.json",
            "CHANGELOG.md"
        ]
        
        # Get current date for archive path
        now = datetime.now()
        self.archive_year = now.strftime("%Y")
        self.archive_month = now.strftime("%m")
        self.archive_path = Path("archives") / self.archive_year / self.archive_month
        
        print(f"Archive path: {self.archive_path}")
    
    def check_existing_files(self):
        """Check which files exist and need to be archived"""
        existing_files = []
        for filename in self.main_files:
            if Path(filename).exists():
                existing_files.append(filename)
        
        print(f"Found {len(existing_files)} files to potentially archive")
        return existing_files
    
    def check_archive_exists(self):
        """Check if archive for this month already exists"""
        if not self.archive_path.exists():
            return False
        
        # Check if main database file exists in archive
        archive_db = self.archive_path / "font-database.json"
        if archive_db.exists():
            print(f"Archive already exists for {self.archive_year}/{self.archive_month}")
            return True
        
        return False
    
    def get_database_version(self, db_file):
        """Get version from database file"""
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("version", "unknown")
        except Exception as e:
            print(f"Could not read version from {db_file}: {e}")
            return "unknown"
    
    def compare_with_archive(self, existing_files):
        """Compare current files with archived version"""
        if not self.check_archive_exists():
            return True  # No archive exists, safe to create
        
        # Compare database versions
        current_db = "font-database.json"
        archive_db = self.archive_path / "font-database.json"
        
        if current_db in existing_files and archive_db.exists():
            current_version = self.get_database_version(current_db)
            archive_version = self.get_database_version(archive_db)
            
            print(f"Current version: {current_version}")
            print(f"Archive version: {archive_version}")
            
            if current_version == archive_version:
                print("Versions match - skipping archive creation")
                return False
            else:
                print("Different versions - will update archive")
                return True
        
        return True
    
    def create_archive(self, existing_files):
        """Create archive of existing files"""
        if not existing_files:
            print("No files to archive")
            return
        
        # Create archive directory
        self.archive_path.mkdir(parents=True, exist_ok=True)
        print(f"Created archive directory: {self.archive_path}")
        
        # Copy files to archive
        archived_count = 0
        for filename in existing_files:
            source = Path(filename)
            destination = self.archive_path / filename
            
            try:
                shutil.copy2(source, destination)
                print(f"Archived: {filename}")
                archived_count += 1
            except Exception as e:
                print(f"Error archiving {filename}: {e}")
        
        # Create archive metadata
        metadata = {
            "archived_date": datetime.now().isoformat() + "Z",
            "archive_path": str(self.archive_path),
            "archived_files": existing_files,
            "file_count": archived_count
        }
        
        # Add database version if available
        if "font-database.json" in existing_files:
            metadata["database_version"] = self.get_database_version("font-database.json")
        
        # Save metadata
        metadata_file = self.archive_path / "archive-metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"Archive completed: {archived_count} files archived to {self.archive_path}")
        return archived_count
    
    def cleanup_old_files(self, files_to_remove):
        """Remove old files after successful archiving"""
        removed_count = 0
        for filename in files_to_remove:
            try:
                if Path(filename).exists():
                    Path(filename).unlink()
                    print(f"Removed old file: {filename}")
                    removed_count += 1
            except Exception as e:
                print(f"Error removing {filename}: {e}")
        
        print(f"Cleanup completed: {removed_count} old files removed")
        return removed_count
    
    def list_archives(self):
        """List all existing archives"""
        archives_root = Path("archives")
        if not archives_root.exists():
            print("No archives directory found")
            return []
        
        archives = []
        for year_dir in sorted(archives_root.iterdir()):
            if year_dir.is_dir():
                for month_dir in sorted(year_dir.iterdir()):
                    if month_dir.is_dir():
                        archive_path = year_dir / month_dir
                        metadata_file = archive_path / "archive-metadata.json"
                        
                        archive_info = {
                            "path": str(archive_path),
                            "year": year_dir.name,
                            "month": month_dir.name
                        }
                        
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                                    archive_info.update(metadata)
                            except Exception as e:
                                print(f"Error reading metadata for {archive_path}: {e}")
                        
                        archives.append(archive_info)
        
        return archives
    
    def run_archive(self, force=False):
        """Main archive execution"""
        print("Starting database archiving process...")
        
        # Check what files exist
        existing_files = self.check_existing_files()
        if not existing_files:
            print("No files found to archive")
            return True
        
        # Check if we should create archive
        if not force and not self.compare_with_archive(existing_files):
            print("Archive creation skipped - no changes detected")
            return True
        
        # Create archive
        archived_count = self.create_archive(existing_files)
        
        if archived_count > 0:
            print(f"Archive created successfully with {archived_count} files")
            return True
        else:
            print("Archive creation failed")
            return False


def main():
    """Main execution function"""
    import sys
    
    archiver = DatabaseArchiver()
    
    # Handle command line arguments
    force = "--force" in sys.argv
    list_archives = "--list" in sys.argv
    
    if list_archives:
        print("=== Existing Archives ===")
        archives = archiver.list_archives()
        if archives:
            for archive in archives:
                version = archive.get("database_version", "unknown")
                file_count = archive.get("file_count", "unknown")
                print(f"{archive['year']}/{archive['month']}: v{version} ({file_count} files)")
        else:
            print("No archives found")
        return 0
    
    success = archiver.run_archive(force=force)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())