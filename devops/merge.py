#!/usr/bin/env python3
"""
Content Merge Script for Book Creator

This script merges markdown files from volume directories according to YAML configuration.
Can be run as a standalone module or called from other scripts via main() function.

Usage:
    python -m merge volumes.yaml [-vol volume-001] [--output output_dir] [--input input_dir]
"""

import argparse
import os
import sys
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


def demote_headers(content: str) -> str:
    """
    Demote all headers in markdown content by one level.
    Supports both # syntax and underline syntax.
    """
    lines = content.split('\n')
    result_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Handle # syntax headers
        if line.strip().startswith('#'):
            # Add one more # to demote
            result_lines.append('#' + line)
        # Handle underline syntax (= and -)
        elif i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip() and all(c in '=' for c in next_line.strip()):
                # H1 with === becomes ## H2
                result_lines.append('## ' + line)
                result_lines.append('')  # Add empty line instead of underline
                i += 1  # Skip the underline
            elif next_line.strip() and all(c in '-' for c in next_line.strip()):
                # H2 with --- becomes ### H3
                result_lines.append('### ' + line)
                result_lines.append('')  # Add empty line instead of underline
                i += 1  # Skip the underline
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)
        
        i += 1
    
    return '\n'.join(result_lines)


def merge_volume(volume_name: str, volume_config: Dict, input_dir: Path, output_dir: Path) -> None:
    """
    Merge all markdown files for a single volume.
    """
    # Determine input path for this volume
    title = volume_config.get('title', volume_name)
    input_name = volume_config.get('input_name', volume_name)
    volume_input_dir = input_dir / input_name
    
    if not volume_input_dir.exists():
        logger.warning(f"Warning: Input directory {volume_input_dir} does not exist, skipping {volume_name}")
        return
    
    # Get all non temporary markdown files in alphabetical order
    md_files = sorted([f for f in volume_input_dir.glob('*.md') if not f.name.endswith('.tmp.md')])
    
    if not md_files:
        logger.warning(f"Warning: No markdown files found in {volume_input_dir}")
        return
    
    logger.info(f"Merging {len(md_files)} files for {volume_name}:")
    
    merged_content = []
    merged_content.append(f"# {title}\n")
    for md_file in md_files:
        logger.debug(f"  - {md_file.name}")
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Demote headers and add to merged content
        demoted_content = demote_headers(content)
        merged_content.append(demoted_content)
    
    # Combine all content
    final_content = '\n\n'.join(merged_content)
    
    # Write merged file
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{volume_name}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    logger.success(f"Created merged file: {output_file}")


def main(args: Optional[List[str]] = None) -> int:
    """
    Main function that can be called from other scripts or command line.
    
    Args:
        args: Command line arguments. If None, uses sys.argv
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='Merge markdown files for book volumes')
    parser.add_argument('config_file', help='YAML configuration file path')
    parser.add_argument('-vol', '--volume', help='Restrict to specific volume (e.g., volume-001)')
    parser.add_argument('--output', help='Output directory (default: current directory)')
    parser.add_argument('--input', help='Input directory (default: current directory)')
    
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    try:
        # Load configuration
        config_path = Path(parsed_args.config_file)
        if not config_path.exists():
            logger.error(f"Error: Configuration file {config_path} not found")
            return 1
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Set up directories
        input_dir = Path(parsed_args.input) if parsed_args.input else Path.cwd()
        output_dir = Path(parsed_args.output) if parsed_args.output else Path.cwd()

        volumes = config.get('volumes', {})
        
        if not volumes:
            logger.error("Error: No volumes found in configuration")
            return 1
        
        # Process volumes
        if parsed_args.volume:
            # Process specific volume
            if parsed_args.volume not in volumes:
                logger.error(f"Error: Volume {parsed_args.volume} not found in configuration")
                return 1
            merge_volume(parsed_args.volume, volumes[parsed_args.volume], input_dir, output_dir)
        else:
            # Process all volumes
            for volume_name, volume_config in volumes.items():
                merge_volume(volume_name, volume_config, input_dir, output_dir)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())