#!/usr/bin/env python3
"""
Unit tests for the Art Deco Book Creator project.

This test suite covers the complete book building process including:
1. Merging markdown files from volumes
2. Entity replacement
3. Custom style application
4. Cleanup operations
5. Complete build process via build-books script

Usage:
    python -m unittest tests.test_artdeco
    python -m unittest tests.test_artdeco.TestArtDecoBookCreator.test_merge_volume_001
"""

import unittest
import sys
import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from loguru import logger

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ensure stdout uses UTF-8 so tests that print emoji don't raise on Windows
try:
    if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    # Best-effort: ignore if reconfigure isn't available
    pass

# Try to import modules - they may not be available in all environments
try:
    from devops import  merge
    from devops import  entitize
    from devops import  customize
    from devops import  build
    from devops import build_books
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some modules not available for direct import: {e}")
    MODULES_AVAILABLE = False


class TestArtDecoBookCreator(unittest.TestCase):
    """Test suite for the Art Deco Book Creator project."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.project_root = project_root
        cls.artdeco_dir = cls.project_root / 'tests' / 'artdeco'
        cls.content_dir = cls.artdeco_dir / 'content'
        cls.test_output_dir = cls.artdeco_dir / 'temp'
        cls.obj_dir = cls.artdeco_dir / 'obj'
        
        # Configuration files
        cls.volumes_config = cls.artdeco_dir / 'volumes.yaml'
        cls.styles_config = cls.artdeco_dir / 'styles.yaml'
        cls.entities_file = cls.artdeco_dir / 'basic.nam'
        
        # Ensure test output directory exists
        cls.test_output_dir.mkdir(exist_ok=True)

                # Configure loguru to write test logs to tests.log inside the test output dir

        # Remove any existing sinks to avoid duplicate logs when reloading tests
        logger.remove()
        log_path = cls.test_output_dir / 'tests.log'
        logger.add(
            str(log_path),
            level="DEBUG",
            enqueue=True,
            encoding="utf-8",
            rotation="10 MB"
        )

    
    def setUp(self):
        """Set up for each individual test."""
        # Clean up any existing test artifacts
        self._cleanup_test_directories()
    
    def tearDown(self):
        """Clean up after each test."""
        self._cleanup_test_directories()
    
    def _cleanup_test_directories(self):
        """Helper method to clean up test directories."""
        directories_to_clean = [
            # Keep final build/bin outputs so the user can inspect them after tests
            self.obj_dir,
            self.test_output_dir / 'obj',
            # Note: do NOT remove 'build' or 'bin' in test_output_dir so outputs remain
            # self.test_output_dir / 'build',
            # self.test_output_dir / 'bin',
            # Also leave project-level build/bin alone
            # self.project_root / 'build',
            # self.project_root / 'bin'
        ]
        
        for directory in directories_to_clean:
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
    
    def _run_python_module(self, module_name, args):
        """Helper method to run a Python module as subprocess."""
        # Run the module directly (avoid changing global cwd)
        cmd = [sys.executable, '-m', f'devops.{module_name}'] + args
        try:
            result = subprocess.run(
                cmd, 
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Process timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def _run_build_books(self, args):
        """Helper method to run build-books as a module via -m.

        Automatically injects volumes.yaml, styles.yaml and basic.nam from
        tests/artdeco when not asking for help and when those files exist.
        """
        # Skip adding config files when caller requests help
        if any(a in ('-h', '--help') or (isinstance(a, str) and a.startswith('-h')) for a in args):
            cmd = [sys.executable, '-m', 'devops.build_books'] + args
        else:
            # Build path to config files from the test artdeco directory
            artdeco = self.project_root / 'tests' / 'artdeco'
            vols = artdeco / 'volumes.yaml'
            styles = artdeco / 'styles.yaml'
            entities = artdeco / 'basic.nam'

            # Only add existing config files and avoid duplication
            cfg_args = []
            if vols.exists() and str(vols) not in args:
                cfg_args.append(str(vols))
            if styles.exists() and str(styles) not in args:
                cfg_args.append(str(styles))
            if entities.exists() and str(entities) not in args:
                cfg_args.append(str(entities))

            cmd = [sys.executable, '-m', 'devops.build_books'] + cfg_args + args

        # Run the build from the tests/artdeco fixture directory so that
        # merge will read the test content (tests/artdeco/content/*).
        artdeco_cwd = self.project_root / 'tests' / 'artdeco'
        try:
            # Ensure the subprocess can import the devops package by adding
            # the project root to PYTHONPATH while running from the fixture cwd.
            env = os.environ.copy()
            existing = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = str(self.project_root) + (os.pathsep + existing if existing else '')

            result = subprocess.run(
                cmd,
                cwd=str(artdeco_cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout for full builds
            )
            # Persist child stdout/stderr and the exact command to files inside the
            # test output directory so we can inspect pandoc invocation and loguru output
            try:
                log_dir = self.test_output_dir
                log_dir.mkdir(parents=True, exist_ok=True)

                # Append full child info to main tests.log for convenience
                with open(log_dir / 'tests.log', 'a', encoding='utf-8') as lof:
                    lof.write('\n===== CHILD PROCESS CMD =====\n')
                    lof.write(' '.join(map(str, cmd)) + '\n')
                    lof.write('----- STDOUT -----\n')
                    lof.write(result.stdout or '')
                    lof.write('\n----- STDERR -----\n')
                    lof.write(result.stderr or '')
                    lof.write('\n===== END CHILD PROCESS =====\n')

                # Separate files for programmatic inspection
                (log_dir / 'child_stdout.log').write_text(result.stdout or '', encoding='utf-8')
                (log_dir / 'child_stderr.log').write_text(result.stderr or '', encoding='utf-8')
                (log_dir / 'child_cmd.txt').write_text(' '.join(map(str, cmd)), encoding='utf-8')

                # Persist any input markdowns that were created under the fixture obj/custom
                try:
                    src_obj_custom = artdeco_cwd / 'obj' / 'custom'
                    saved_inputs = log_dir / 'saved_inputs'
                    if src_obj_custom.exists():
                        saved_inputs.mkdir(parents=True, exist_ok=True)
                        for md in src_obj_custom.glob('*.md'):
                            shutil.copy(md, saved_inputs / md.name)
                except Exception:
                    # don't fail on this secondary logging step
                    pass

                # Extract content.xml from any produced ODTs for quick include checks
                try:
                    from zipfile import ZipFile
                    odt_extract_dir = log_dir / 'odt_contents'
                    odt_extract_dir.mkdir(parents=True, exist_ok=True)

                    # Determine output directory: try to find it among cmd args
                    out_dir = None
                    for i, a in enumerate(cmd[:-1]):
                        if isinstance(a, str) and a == '--output' and i + 1 < len(cmd):
                            out_dir = Path(cmd[i+1])
                            break
                    if out_dir is None:
                        out_dir = log_dir

                    for odt in Path(out_dir).glob('*.odt'):
                        target_dir = odt_extract_dir / odt.stem
                        target_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            with ZipFile(odt, 'r') as z:
                                if 'content.xml' in z.namelist():
                                    with z.open('content.xml') as cf:
                                        content_xml = cf.read().decode('utf-8')
                                        (target_dir / 'content.xml').write_text(content_xml, encoding='utf-8')
                                        # Quick check for include placeholders
                                        report_lines = []
                                        if 'INCLUDE:' in content_xml or 'INCLUDE_PLACEHOLDER' in content_xml or 'hatched_rect' in content_xml:
                                            report_lines.append(f"Include-like content found in {odt.name}")
                                        else:
                                            report_lines.append(f"No include content found in {odt.name}")
                                        # append to include_report.txt
                                        with open(log_dir / 'include_report.txt', 'a', encoding='utf-8') as ir:
                                            ir.write('\n'.join(report_lines) + '\n')
                        except Exception:
                            continue
                except Exception:
                    pass

            except Exception:
                # Best-effort: don't let logging failures break the test helper
                pass

            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Process timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def test_build_books_complete_process(self):
        """Test the complete build-books process for all volumes."""
        print("\\n=== Testing complete build-books process ===")
        
        # Ensure we start with clean directories
        self._cleanup_test_directories()
        
        # Test build-books with all volumes to test output directory
        test_build_dir = self.test_output_dir / 'build'
        
        # Use subprocess to run build-books (only pass output; keep tests simple)
        args = ['--output', str(test_build_dir)]
        result, stdout, stderr = self._run_build_books(args)
        print(f"   Build-books exit code: {result}")
        if stdout:
            print("📥 ================ STDOUT =============== ")
            print(stdout)
        if stderr:
            print("🚨 ================ STDERR =============== ")
            print(f"   stderr: {stderr[-500:]}")  # Last 1000 chars

        # Require that build produced at least one PDF in the final output dir
        pdfs = list(test_build_dir.glob('*.pdf')) if test_build_dir.exists() else []
        self.assertGreater(
            len(pdfs), 0,
            f"Expected at least one PDF in {test_build_dir}. stdout:\n{stdout}\nstderr:\n{stderr}"
        )
        
        if test_build_dir.exists():
            output_files = list(test_build_dir.glob('*'))
            print(f"   Build output files: {[f.name for f in output_files]}")
        
        print("✅ Build-books process completed")
    
    def test_build_books_volume_001_only(self):
        """Test the build-books process for volume-001 only."""
        print("\\n=== Testing build-books for volume-001 only ===")
        
        # Ensure we start with clean directories
        self._cleanup_test_directories()
        # Test build-books with specific volume to build directory
        test_build_dir = self.test_output_dir / 'build'
        
        # Use subprocess to run build-books (only pass output and volume flag)
        args = ['--output', str(test_build_dir), '-vol', 'volume-001']
        result, stdout, stderr = self._run_build_books(args)

        print(f"   Build-books exit code: {result}")
        if stdout:
            print(f"   stdout: {stdout[-500:]}")  # Last 500 chars
        if stderr:
            print(f"   stderr: {stderr[-500:]}")  # Last 500 chars
        
        # Require that build produced at least one PDF in the final output dir
        pdfs = list(test_build_dir.glob('*.pdf')) if test_build_dir.exists() else []
        self.assertGreater(
            len(pdfs), 0,
            f"Expected at least one PDF in {test_build_dir}. stdout:\n{stdout}\nstderr:\n{stderr}"
        )
        
        # Optionally log intermediate files if present
        obj_dir = self.project_root / 'obj'
        if obj_dir.exists():
            merged_file = obj_dir / 'volume-001.md'
            unicode_file = obj_dir / 'unicode' / 'volume-001.md'
            custom_file = obj_dir / 'custom' / 'volume-001.md'
            print(f"   Merged file exists: {merged_file.exists()}")
            print(f"   Unicode file exists: {unicode_file.exists()}")
            print(f"   Custom file exists: {custom_file.exists()}")

        if test_build_dir.exists():
            output_files = list(test_build_dir.glob('*'))
            print(f"   Final output files: {[f.name for f in output_files]}")
        
        print("✅ Build-books for volume-001 completed")
    
    def test_individual_modules_exist(self):
        """Test that all required modules can be imported."""
        print("\\n=== Testing module imports ===")
        
        if MODULES_AVAILABLE:
            modules = [
                ('merge', merge),
                ('entitize', entitize), 
                ('customize', customize),
                ('build', build),
                ('build_books', build_books)
            ]
            
            for module_name, module in modules:
                self.assertIsNotNone(module, f"Module {module_name} should be importable")
                self.assertTrue(hasattr(module, 'main'), f"Module {module_name} should have main function")
                print(f"   ✅ {module_name} module imported successfully")
        else:
            # Test modules via subprocess calls
            module_names = ['merge', 'entitize', 'customize', 'build']
            for module_name in module_names:
                result, stdout, stderr = self._run_python_module(module_name, ['--help'])
                # Help should work and show usage information
                self.assertIn('usage:', stdout.lower(), f"Module {module_name} should show usage help")
                print(f"   ✅ {module_name} module accessible via subprocess")
            
            # Test build-books separately
            result, stdout, stderr = self._run_build_books(['--help'])
            self.assertIn('usage:', stdout.lower(), "build-books should show usage help")
            print(f"   ✅ build-books script accessible via subprocess")
    
    def test_configuration_files_exist(self):
        """Test that all required configuration files exist."""
        print("\\n=== Testing configuration files ===")
        
        config_files = [
            ('volumes.yaml', self.volumes_config),
            ('styles.yaml', self.styles_config),
            ('basic.nam', self.entities_file)
        ]
        
        for name, path in config_files:
            self.assertTrue(path.exists(), f"Configuration file {name} should exist at {path}")
            self.assertGreater(path.stat().st_size, 0, f"Configuration file {name} should not be empty")
            print(f"   ✅ {name} exists and has content")
    
    def test_content_directories_exist(self):
        """Test that content directories and files exist."""
        print("\\n=== Testing content structure ===")
        
        # Check content directory exists
        self.assertTrue(self.content_dir.exists(), f"Content directory should exist: {self.content_dir}")
        
        # Check volume directories
        volume_dirs = ['volume-001', 'volume-002']
        for vol_dir in volume_dirs:
            vol_path = self.content_dir / vol_dir
            if vol_path.exists():
                md_files = list(vol_path.glob('*.md'))
                print(f"   ✅ {vol_dir}: {len(md_files)} markdown files")
                self.assertGreater(len(md_files), 0, f"Volume {vol_dir} should contain markdown files")
            else:
                print(f"   ⚠️  {vol_dir}: directory not found")



def run_tests():
    """Helper function to run all tests with detailed output."""
    # Configure test runner for verbose output
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestArtDecoBookCreator))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("ART DECO BOOK CREATOR - UNIT TEST SUITE")
    print("=" * 60)
    
    # Run tests
    success = run_tests()
    
    print("\\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("=" * 60)
    
    sys.exit(0 if success else 1)