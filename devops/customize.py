#!/usr/bin/env python3
"""
Custom Styles Script for Book Creator

This script applies custom styles to markdown files using regular expression patterns.
Can be run as a standalone module or called from other scripts via main() function.

Usage:
    python -m customize styles.yaml file1.md [file2.md ...] [--output output_dir]
"""

import argparse
import os
import sys
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger


def load_styles(styles_file: Path) -> Dict[str, Any]:
    """
    Load style definitions from a YAML file.
    
    Args:
        styles_file: Path to the styles YAML file
    
    Returns:
        Dictionary containing style definitions
    """
    with open(styles_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def apply_styles(content: str, styles_config: Dict[str, Any]) -> str:
    """
    Apply custom styles to markdown content using regex patterns.
    
    Args:
        content: Markdown content
        styles_config: Style configuration from YAML
    
    Returns:
        Content with styles applied
    """
    styles = styles_config.get('styles', {})
    
    for style_name, style_def in styles.items():
        patterns = style_def.get('patterns', [])
        
        for pattern_def in patterns:
            pattern = pattern_def.get('pattern', '')
            replacement = pattern_def.get('replacement', '')
            
            if pattern and replacement:
                try:
                    # Apply the regex pattern
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                    logger.debug(f"Applied style '{style_name}' with pattern: {pattern}")
                except re.error as e:
                    logger.warning(f"Warning: Invalid regex pattern in style '{style_name}': {pattern} - {e}")
    
    return content


def process_file(input_file: Path, output_dir: Path, styles_config: Dict[str, Any]) -> Path:
    """
    Process a single markdown file to apply custom styles.
    
    Args:
        input_file: Input markdown file
        output_dir: Output directory
        styles_config: Style configuration
    
    Returns:
        Path to the output file
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply styles but avoid modifying fences of the form:
    # ::: {.... src="..." ...}
    # :::
    # We scan the file line-by-line and skip replacements while inside a fenced block.
    lines = content.splitlines(keepends=True)
    out_lines = []
    buffer = []
    in_fenced = False

    for line in lines:
        stripped = line.strip()
        # Detect start of include fence: line starts with ':::'
        if not in_fenced and stripped.startswith(':::'):
            # flush buffer (apply styles to accumulated non-fenced lines)
            if buffer:
                segment = ''.join(buffer)
                out_lines.append(apply_styles(segment, styles_config))
                buffer = []
            in_fenced = True
            out_lines.append(line)
            continue

        # Detect end of include fence
        if in_fenced:
            out_lines.append(line)
            if stripped == ':::':
                in_fenced = False
            continue

        # Normal content - accumulate for styled processing
        buffer.append(line)

    # flush any remaining buffer
    if buffer:
        segment = ''.join(buffer)
        out_lines.append(apply_styles(segment, styles_config))

    processed_content = ''.join(out_lines)
    
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
    parser = argparse.ArgumentParser(description='Apply custom styles to markdown files')
    parser.add_argument('styles_file', help='Path to the styles YAML file')
    parser.add_argument('files', nargs='+', help='Markdown files to process')
    parser.add_argument('--output', help='Output directory (default: current directory)')
    
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    try:
        # Load styles
        styles_file = Path(parsed_args.styles_file)
        if not styles_file.exists():
            logger.error(f"Error: Styles file {styles_file} not found")
            return 1
        
        styles_config = load_styles(styles_file)
        logger.info(f"Loaded styles from {styles_file}")
        
        # Set up output directory
        output_dir = Path(parsed_args.output) if parsed_args.output else Path.cwd()
        
        # Process files
        processed_files = []
        for file_path in parsed_args.files:
            input_file = Path(file_path)
            if not input_file.exists():
                print(f"Warning: File {input_file} not found, skipping")
                continue
            
            print(f"Processing {input_file}")
            output_file = process_file(input_file, output_dir, styles_config)
            processed_files.append(output_file)
            print(f"  -> {output_file}")
        
        print(f"Successfully processed {len(processed_files)} files")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())