#!/usr/bin/env python3
"""
Logging Configuration for Book Creator

This module provides centralized logging configuration using loguru.
Import this module at the beginning of your scripts to set up consistent logging.
"""

from loguru import logger
import sys
from pathlib import Path


def setup_logging(level="INFO", log_file=None, format_string=None):
    """
    Configure loguru logging for the book creator project.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        format_string: Optional custom format string
    """
    # Remove default handler
    logger.remove()
    
    # Default format with colors for console
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
    
    # Add console handler with colors
    logger.add(
        sys.stderr,
        format=format_string,
        level=level,
        colorize=True
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # File format without colors
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        )
        
        logger.add(
            log_path,
            format=file_format,
            level=level,
            rotation="10 MB",
            retention="1 week"
        )
    
    return logger


# Default setup - can be imported and used immediately
setup_logging()