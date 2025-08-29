#!/usr/bin/env python3
"""
DXT Package Creator for ra-3 Research Assistant
Creates a .dxt extension archive for one-click installation in Claude Desktop
"""

import os
import shutil
import subprocess
import zipfile
import json
import argparse
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

class DXTPackager:
    def __init__(self, source_dir: str, output_dir: str = "dist", name: Optional[str] = None, verbose: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.verbose = verbose
        self.temp_dir: Optional[Path] = None
        
        # Determine output filename
        if name:
            self.output_name = name if name.endswith('.dxt') else f"{name}.dxt"
        else:
            self.output_name = f"{self.source_dir.name}.dxt"
            
        self.output_path = self.output_dir / self.output_name
        
    def log(self, message: str) -> None:
        """Print message if verbose mode is enabled"""
        if self.verbose:
            print(f"[DXT] {message}")
            
    def error(self, message: str) -> None:
        """Print error message and exit"""
        print(f"[ERROR] {message}", file=sys.stderr)
        sys.exit(1)
        
    def validate_source_structure(self) -> None:
        """Validate that source directory has required DXT structure"""
        self.log("Validating source directory structure...")
        
        if not self.source_dir.exists():
            self.error(f"Source directory does not exist: {self.source_dir}")
            
        manifest_path = self.source_dir / "manifest.json"
        if not manifest_path.exists():
            self.error("manifest.json not found in source directory")
            
        server_dir = self.source_dir / "server"
        if not server_dir.exists():
            self.error("server/ directory not found")
            
        main_py = server_dir / "main.py"
        if not main_py.exists():
            self.error("server/main.py not found")
            
        self.log("Source structure validation passed")
        
    def validate_manifest(self) -> Dict[str, Any]:
        """Load and validate manifest.json"""
        self.log("Validating manifest.json...")
        
        manifest_path = self.source_dir / "manifest.json"
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            self.error(f"Invalid JSON in manifest.json: {e}")
        except Exception as e:
            self.error(f"Error reading manifest.json: {e}")
            
        # Validate required fields
        required_fields = ["dxt_version", "name", "version", "server"]
        for field in required_fields:
            if field not in manifest:
                self.error(f"Required field '{field}' missing from manifest.json")
                
        # Validate server configuration
        server_config = manifest.get("server", {})
        if server_config.get("type") != "python":
            self.error("Only Python servers are supported")
            
        if "entry_point" not in server_config:
            self.error("server.entry_point missing from manifest.json")
            
        self.log("Manifest validation passed")
        return manifest
        
    def bundle_dependencies(self) -> None:
        """Install Python dependencies to lib/ directory"""
        self.log("Bundling Python dependencies...")
        
        requirements_path = self.source_dir / "requirements.txt"
        if not requirements_path.exists():
            self.log("No requirements.txt found, skipping dependency bundling")
            return
            
        lib_dir = self.temp_dir / "lib"
        lib_dir.mkdir(exist_ok=True)
        
        try:
            # Install dependencies to lib directory
            cmd = [
                sys.executable, "-m", "pip", "install",
                "-r", str(requirements_path),
                "--target", str(lib_dir),
                "--upgrade",
                "--force-reinstall",
                "--no-deps"  # Avoid dependency conflicts
            ]
            
            self.log(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.error(f"Failed to install dependencies: {result.stderr}")
                
            self.log("Dependencies bundled successfully")
            
        except Exception as e:
            self.error(f"Error bundling dependencies: {e}")
            
    def copy_extension_files(self) -> None:
        """Copy extension files to temp directory"""
        self.log("Copying extension files...")
        
        # Copy manifest.json
        shutil.copy2(
            self.source_dir / "manifest.json",
            self.temp_dir / "manifest.json"
        )
        
        # Copy server directory
        server_src = self.source_dir / "server"
        server_dst = self.temp_dir / "server"
        shutil.copytree(server_src, server_dst)
        
        # Copy optional files if they exist
        optional_files = ["requirements.txt", "README.md", "LICENSE", "icon.png"]
        for filename in optional_files:
            src_file = self.source_dir / filename
            if src_file.exists():
                shutil.copy2(src_file, self.temp_dir / filename)
                self.log(f"Copied optional file: {filename}")
                
        self.log("Extension files copied successfully")
        
    def create_dxt_archive(self) -> None:
        """Create the .dxt ZIP archive"""
        self.log(f"Creating DXT archive: {self.output_path}")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files from temp directory
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        # Get relative path from temp_dir
                        arc_path = file_path.relative_to(self.temp_dir)
                        zipf.write(file_path, arc_path)
                        
            self.log(f"DXT archive created successfully: {self.output_path}")
            
        except Exception as e:
            self.error(f"Failed to create DXT archive: {e}")
            
    def cleanup(self) -> None:
        """Clean up temporary directory"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.log("Cleaned up temporary files")
            
    def package(self) -> str:
        """Main packaging process"""
        try:
            # Validate inputs
            self.validate_source_structure()
            manifest = self.validate_manifest()
            
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="dxt_package_"))
            self.log(f"Created temporary directory: {self.temp_dir}")
            
            # Packaging steps
            self.copy_extension_files()
            self.bundle_dependencies()
            self.create_dxt_archive()
            
            return str(self.output_path)
            
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Package ra-3 Research Assistant as a Claude DXT extension"
    )
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=".",
        help="Source directory containing the extension (default: current directory)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="dist",
        help="Output directory for the .dxt file (default: dist)"
    )
    parser.add_argument(
        "--name", "-n",
        help="Output filename (default: source directory name)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    packager = DXTPackager(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        name=args.name,
        verbose=args.verbose
    )
    
    try:
        output_path = packager.package()
        print(f"✅ Successfully created DXT extension: {output_path}")
        print(f"📁 Archive size: {Path(output_path).stat().st_size:,} bytes")
        print("🚀 Ready for installation in Claude Desktop!")
        
    except KeyboardInterrupt:
        print("\n❌ Packaging interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()