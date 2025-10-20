#!/usr/bin/env python3
"""
Entity Replacement Script for Book Creator

This script replaces named entities in markdown files with their Unicode counterparts.
Can be run as a standalone module or called from other scripts via main() function.

Usage:
    python -m entitize entities.nam file1.md [file2.md ...] [--output output_dir]
"""

import argparse
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


def load_entities(entities_file: Path) -> Dict[str, str]:
    """
    Load entity definitions from a .nam file.
    
    Args:
        entities_file: Path to the .nam file
    
    Returns:
        Dictionary mapping entity names to Unicode characters
    """
    entities = {}
    
    with open(entities_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    hex_code = parts[0]
                    if hex_code.startswith('0x'):
                        try:
                            unicode_char = chr(int(hex_code, 16))
                            entities[name] = unicode_char
                        except ValueError:
                            logger.warning(f"Warning: Invalid hex code {hex_code} for entity {name}")
    
    return entities


def replace_entities(content: str, entities: Dict[str, str]) -> str:
    """
    Replace entity references in content with Unicode characters.
    
    Args:
        content: Markdown content
        entities: Dictionary mapping entity names to Unicode characters
    
    Returns:
        Content with entities replaced
    """
    def replace_entity(match):
        entity_name = match.group(1)
        if entity_name in entities:
            return entities[entity_name]
        else:
            # Return the original if entity not found
            logger.warning(f"Warning: Unknown entity &{entity_name};")
            return match.group(0)
    
    # Pattern to match &entityname;
    pattern = r'&([a-zA-Z][a-zA-Z0-9_]*);'
    return re.sub(pattern, replace_entity, content)


def process_file(input_file: Path, output_dir: Path, entities: Dict[str, str]) -> Path:
    """
    Process a single markdown file to replace entities.
    
    Args:
        input_file: Input markdown file
        output_dir: Output directory
        entities: Entity mappings
    
    Returns:
        Path to the output file
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace entities
    processed_content = replace_entities(content, entities)
    
    # Write to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / input_file.name
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(processed_content)
    
    return output_file


def main(args: Optional[List[str]] = None) -> int:
    """
    Main function that can be called from other scripts or command line.
    
    Args:
        args: Command line arguments. If None, uses sys.argv
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='Replace named entities in markdown files')
    parser.add_argument('entities_file', help='Path to the entities (.nam) file')
    parser.add_argument('files', nargs='+', help='Markdown files to process')
    parser.add_argument('--output', help='Output directory (default: current directory)')
    
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    try:
        # Load entities
        entities_file = Path(parsed_args.entities_file)
        if not entities_file.exists():
            logger.error(f"Error: Entities file {entities_file} not found")
            return 1
        
        entities = load_entities(entities_file)
        logger.info(f"Loaded {len(entities)} entities from {entities_file}")
        
        # Set up output directory
        output_dir = Path(parsed_args.output) if parsed_args.output else Path.cwd()
        
        # Process files
        processed_files = []
        for file_path in parsed_args.files:
            input_file = Path(file_path)
            if not input_file.exists():
                logger.warning(f"Warning: File {input_file} not found, skipping")
                continue
            
            logger.info(f"Processing {input_file}")
            output_file = process_file(input_file, output_dir, entities)
            processed_files.append(output_file)
            logger.debug(f"  -> {output_file}")
        
        logger.success(f"Successfully processed {len(processed_files)} files")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())