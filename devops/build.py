#!/usr/bin/env python3
"""
Production Script for Book Creator

This script handles the production phase: converting markdown to ODT and PDF using Pandoc.
Can be run as a standalone module or called from other scripts via main() function.

Usage:
    python -m build config.yaml [-vol volume-001] [--output output_dir] [--input input_dir]
"""

import argparse
import os
import sys
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger


def run_pandoc_odt(input_file: Path, output_file: Path, template_file: Path, 
                   pandoc_options: List[str], resource_path: str = "") -> bool:
    """
    Convert markdown to ODT using Pandoc.
    
    Args:
        input_file: Input markdown file
        output_file: Output ODT file
        template_file: Template OTT file
        pandoc_options: Additional Pandoc options
        resource_path: Resource path for Pandoc
    
    Returns:
        True if successful, False otherwise
    """
    cmd = [
        'pandoc',
        str(input_file),
        f'--reference-doc={template_file}',
        f'--output={output_file}',
        '--verbose', 
        '--embed-resources', 
    ]
    
    if resource_path:
        cmd.append(f'--resource-path={resource_path}')
    
    cmd.extend(pandoc_options)
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stdout:
            logger.debug(f"Pandoc output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Pandoc: {e}")
        if e.stderr:
            logger.error(f"Pandoc error: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("Error: Pandoc not found. Please install Pandoc.")
        return False


def run_libreoffice_pdf(input_file: Path, output_dir: Path) -> bool:
    """
    Convert ODT to PDF using LibreOffice.
    
    Args:
        input_file: Input ODT file
        output_dir: Output directory for PDF
        pdf_export_options: LibreOffice PDF export options
    
    Returns:
        True if successful, False otherwise
    """
    # Try different common LibreOffice executable names and paths
    libreoffice_commands = [
        'libreoffice',
        'soffice',
        r'C:\Program Files\LibreOffice\program\soffice.exe',
        r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'
    ]

    for cmd_base in libreoffice_commands:
        cmd = [
            cmd_base,
            '--headless',
            f'--convert-to',
            'pdf:writer_pdf_Export',
            str(input_file),
            f'--outdir',
            str(output_dir)
        ]
        
        logger.debug(f"Trying: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Executed: {' '.join(cmd)}")
            if result.stdout:
                logger.debug(f"LibreOffice output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running LibreOffice with {cmd_base}: {e}")
            if e.stderr:
                logger.error(f"LibreOffice error: {e.stderr}")
            
            # Check if PDF was created despite the error
            pdf_file = output_dir / (input_file.stem + '.pdf')
            if pdf_file.exists():
                logger.info(f"PDF was created successfully despite exit code: {pdf_file}")
                return True
            # If PDF wasn't created, continue to next command
            continue
            
        except FileNotFoundError:
            logger.debug(f"LibreOffice not found at: {cmd_base}")
            continue
    
    logger.error("Error: LibreOffice not found. Please install LibreOffice or add it to PATH.")
    logger.warning("Continuing without PDF generation...")
    return False


def build_volume(volume_name: str, volume_config: Dict[str, Any], 
                input_dir: Path, output_dir: Path) -> bool:
    """
    Build a single volume (markdown -> ODT -> PDF).
    
    Args:
        volume_name: Name of the volume
        volume_config: Volume configuration
        input_dir: Input directory containing processed markdown
        output_dir: Output directory for final files
        config: Global configuration
    
    Returns:
        True if successful, False otherwise
    """
    
    # Get paths - resolve relative to the project root
    devops_dir = Path(__file__).parent  # devops directory
    current_dir = Path.cwd()
    
    template_file = current_dir / volume_config.get('template', 'templates/Default.ott')
    
    if not template_file.exists():
        logger.error(f"Error: Template file {template_file} not found")
        return False
    
    # Input and output files
    input_file = input_dir / f"{volume_name}.md"
    if not input_file.exists():
        logger.error(f"Error: Input file {input_file} not found")
        return False
    
    output_name = volume_config.get('output_name', volume_name)
    odt_file = output_dir / f"{output_name}.odt"
    pdf_file = output_dir / f"{output_name}.pdf"
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get Pandoc options and resolve filter paths
    pandoc_options = [
        "--lua-filter=odt-custom-styles.lua",
        "--lua-filter=odt-bib-style.lua",
        "--lua-filter=fodt-include.lua",
    ]
    
    # Resolve relative paths in pandoc options
    resolved_options = []
    for option in pandoc_options:
        if option.startswith('--lua-filter=') and not option.startswith('--lua-filter=/'):
            # Resolve relative filter path
            filter_path = option.replace('--lua-filter=', '')
            resolved_filter_path = devops_dir/ 'filters' / filter_path
            resolved_options.append(f'--lua-filter={resolved_filter_path}')
        else:
            resolved_options.append(option)

    resource_path = current_dir / 'resources'

    logger.info(f"Building {volume_name} -> {output_name}")
    
    # Convert to ODT
    logger.info(f"Converting {input_file} to ODT...")
    if not run_pandoc_odt(input_file, odt_file, template_file, resolved_options, resource_path):
        return False
    
    logger.success(f"Created: {odt_file}")
    
    # Convert to PDF
    logger.info(f"Converting {odt_file} to PDF...")
    if run_libreoffice_pdf(odt_file, output_dir):
        logger.success(f"Created: {pdf_file}")
    else:
        logger.warning(f"Warning: PDF generation failed, but ODT file was created successfully: {odt_file}")
    
    return True


def main(args: Optional[List[str]] = None) -> int:
    """
    Main function that can be called from other scripts or command line.
    
    Args:
        args: Command line arguments. If None, uses sys.argv
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='Build books from processed markdown files')
    parser.add_argument('config_file', help='YAML configuration file path')
    parser.add_argument('-vol', help='Restrict to specific volume (e.g., volume-001)')
    parser.add_argument('--output', help='Output directory (default: build)')
    parser.add_argument('--input', help='Input directory with processed markdown files')
    
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    try:
        # Load configuration
        config_path = Path(parsed_args.config_file)
        if not config_path.exists():
            print(f"Error: Configuration file {config_path} not found")
            return 1
        

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Set up directories
        default_output = 'build'
        output_dir = Path(parsed_args.output) if parsed_args.output else Path(default_output)
        
        if parsed_args.input:
            input_dir = Path(parsed_args.input)
        else:
            input_dir = Path('obj') / 'custom'
        
        volumes = config.get('volumes', {})
        
        if not volumes:
            print("Error: No volumes found in configuration")
            return 1
        
        # Build volumes
        success = True
        if parsed_args.vol:
            # Build specific volume
            if parsed_args.vol not in volumes:
                print(f"Error: Volume {parsed_args.vol} not found in configuration")
                return 1
            success = build_volume(parsed_args.vol, volumes[parsed_args.vol], input_dir, output_dir)
        else:
            # Build all volumes
            for volume_name, volume_config in volumes.items():
                if not build_volume(volume_name, volume_config, input_dir, output_dir):
                    success = False
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())