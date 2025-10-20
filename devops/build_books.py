#!/usr/bin/env python3
"""
Build Books Script for Book Creator

This script orchestrates the complete book building process by calling all the individual
processing scripts in the correct order.

Usage:
    python build-books.py volume_list styles name_list [-vol volume-001] [--output output_dir]
"""

import argparse
import sys
import os
from pathlib import Path
from loguru import logger

# Add devops directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

import merge
import entitize
import customize
import build


def main():
    """Main function for the build-books script."""
    parser = argparse.ArgumentParser(description='Build books from markdown content')
    parser.add_argument('volume_list', help='Path to volumes.yaml file')
    parser.add_argument('styles', help='Path to styles.yaml file')
    parser.add_argument('name_list', help='Path to name entities file (e.g., basic.nam)')
    parser.add_argument('-vol', help='Restrict to specific volume (e.g., volume-001)')
    parser.add_argument('--output', default='build', 
                       help='Output directory (default: build)')
    parser.add_argument('--temp', default='obj',
                       help='Temporary directory (default: obj)')

    args = parser.parse_args()
    
    # Set up paths
    current_dir = Path.cwd()
    config_file = Path(args.volume_list)
    styles_file = Path(args.styles)
    entities_file = Path(args.name_list)
    
    # Create obj directories
    obj_dir = Path(args.temp)
    obj_dir.mkdir(parents=True, exist_ok=True)
    unicode_dir = obj_dir / 'unicode'
    custom_dir = obj_dir / 'custom'

    # Output directory
    final_output_dir = Path(args.output)
    final_output_dir.mkdir(parents=True, exist_ok=True)


    logger.info("=== Book Building Process ===")
    logger.info(f"Project root: {current_dir}")
    logger.info(f"Config files: {config_file}, {styles_file}, {entities_file}")
    logger.info(f"Output directory: {final_output_dir}")
    logger.info(f"Temp directory: {obj_dir}")
    if args.vol:
        logger.info(f"Building volume: {args.vol}")
    else:
        logger.info("Building all volumes")
    logger.info("")
    
    # Step 1: Merge content
    logger.info("Step 1: Merging markdown files...")
    merge_args = [str(config_file), '--output', str(obj_dir), '--input', str(current_dir)]
    if args.vol:
        merge_args.extend(['-vol', args.vol])

    if merge.main(merge_args) != 0:
        logger.error("Error in merge step")
        return 1
    logger.info("")
    
    # Step 2: Entity replacement
    logger.info("Step 2: Replacing entities...")
    
    # Find merged files to process
    merged_files = []
    if args.vol:
        merged_file = obj_dir / f"{args.vol}.md"
        if merged_file.exists():
            merged_files.append(str(merged_file))
    else:
        merged_files = [str(f) for f in obj_dir.glob('*.md')]
    
    if not merged_files:
        logger.error("Error: No merged files found to process")
        return 1
    
    entitize_args = [str(entities_file)] + merged_files + ['--output', str(unicode_dir)]
    
    if entitize.main(entitize_args) != 0:
        logger.error("Error in entitize step")
        return 1
    logger.info("")
    
    # Step 3: Apply custom styles
    logger.info("Step 3: Applying custom styles...")
    
    # Find unicode files to process
    unicode_files = []
    if args.vol:
        unicode_file = unicode_dir / f"{args.vol}.md"
        if unicode_file.exists():
            unicode_files.append(str(unicode_file))
    else:
        unicode_files = [str(f) for f in unicode_dir.glob('*.md')]
    
    if not unicode_files:
        logger.error("Error: No unicode files found to process")
        return 1
    
    customize_args = [str(styles_file)] + unicode_files + ['--output', str(custom_dir)]
    
    if customize.main(customize_args) != 0:
        logger.error("Error in customize step")
        return 1
    logger.info("")
    
    # Step 4: Build final documents
    logger.info("Step 4: Building final documents (ODT and PDF)...")
    
    build_args = [str(config_file), '--input', str(custom_dir), '--output', str(final_output_dir)]
    if args.vol:
        build_args.extend(['-vol', args.vol])
    
    if build.main(build_args) != 0:
        logger.error("Error in build step")
        return 1
    logger.info("")
    
    logger.success("=== Build Complete ===")
    print(f"Final documents available in: {final_output_dir}")
    
    # List generated files
    if final_output_dir.exists():
        odt_files = list(final_output_dir.glob('*.odt'))
        pdf_files = list(final_output_dir.glob('*.pdf'))
        
        if odt_files:
            print("ODT files:")
            for f in odt_files:
                print(f"  - {f.name}")
        
        if pdf_files:
            print("PDF files:")
            for f in pdf_files:
                print(f"  - {f.name}")
    
    return 0


if __name__ == '__main__':
    ret_val = main()
    sys.exit(ret_val)