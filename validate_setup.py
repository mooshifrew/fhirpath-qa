#!/usr/bin/env python3
"""
Quick validation script for FHIR-QA setup.

This script tests the core functionality without requiring a full FHIR server setup.
Run this to verify your installation works correctly.
"""

import sys
import json
from pathlib import Path


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        import fhirpath_gen

        print("✅ fhirpath_gen imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import fhirpath_gen: {e}")
        return False

    try:
        from fhirpath_gen.base import template_registry

        print("✅ template_registry imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import template_registry: {e}")
        return False

    try:
        from fhirpath_gen.generator import create_patient_specific_context

        print("✅ create_patient_specific_context imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import create_patient_specific_context: {e}")
        return False

    return True


def test_templates():
    """Test that templates are properly registered."""
    print("\nTesting template registration...")

    try:
        from fhirpath_gen.base import template_registry

        templates = template_registry.list_templates()
        print(f"✅ Found {len(templates)} templates")

        if len(templates) > 0:
            print(f"   First few templates: {templates[:3]}")
            return True
        else:
            print("❌ No templates found")
            return False
    except Exception as e:
        print(f"❌ Error listing templates: {e}")
        return False


def test_patient_bundles():
    """Test if patient bundles directory exists and contains bundles."""
    print("\nTesting patient bundles...")

    from config import PATIENT_BUNDLES_DIR

    bundles_dir = Path(PATIENT_BUNDLES_DIR)
    if bundles_dir.exists():
        bundle_files = list(bundles_dir.glob("*.json"))
        if len(bundle_files) > 0:
            print(f"✅ Found {len(bundle_files)} patient bundles")
            return True
        else:
            print(f"❌ FAIL -- 0 Bundles")
            print("   Patient bundles directory exists but contains no bundle files")
            return False
    else:
        print("⚠️  Patient bundles directory not found")
        print("   This is expected if you haven't downloaded patient data yet")
        return True  # Not a failure, just a warning


def test_question_generation():
    """Test basic question generation."""
    print("\nTesting question generation...")

    try:
        from fhirpath_gen.base import template_registry
        from fhirpath_gen.generator import GenerationContext

        # Test with a simple template
        templates = template_registry.list_templates()
        if not templates:
            print("❌ No templates available for testing")
            return False

        # Use the first available template
        template_id = templates[0]
        print(f"   Testing with template: {template_id}")

        # Create a default context (works without patient data)
        ctx = GenerationContext("10019917")
        template = template_registry.new_template(template_id, gen_ctx=ctx)
        generated = template.regenerate_qa_pair()

        print("✅ Question generation successful")
        print(f"   Generated question: {generated['question'][:100]}...")
        print(f"   Generated query:    {generated['query'][:100]}...")
        return True

    except Exception as e:
        print(f"❌ Error in question generation test: {e}")
        return False


def test_dependencies():
    """Test that required dependencies are available."""
    print("\nTesting dependencies...")

    required_packages = [
        "pydantic",
        "dateutil",  # python-dateutil installs as 'dateutil'
        "requests",
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} available")
        except ImportError:
            print(f"❌ {package} missing")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n❌ Missing packages: {missing_packages}")
        print("   Run: pip install -r requirements.txt")
        return False

    return True


def test_fhirpath_executable():
    """Test that the FHIRPath executable is available and working."""
    print("\nTesting FHIRPath executable...")

    try:
        from config import FHIRPATH_EXE
    except ImportError:
        print("❌ Could not import FHIRPATH_EXE from config")
        return False

    import subprocess
    import shutil

    # Check if the executable exists or is in PATH
    if not Path(FHIRPATH_EXE).exists() and not shutil.which(FHIRPATH_EXE):
        print(f"⚠️  FHIRPath executable not found: {FHIRPATH_EXE}")
        print(
            "   Query evaluation will be disabled, but questions and queries can still be generated"
        )
        print("   To enable evaluation:")
        print(
            "   1. Download from: https://github.com/octofhir/octofhir-fhirpath/releases"
        )
        print("   2. Or install with: cargo install octofhir-fhirpath")
        print("   3. Update FHIRPATH_EXE in config.py")
        return False

    # Try to run the executable with --help
    try:
        result = subprocess.run(
            [FHIRPATH_EXE, "--help"], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            print(f"✅ FHIRPath executable working: {FHIRPATH_EXE}")
            return True
        else:
            print(f"⚠️  FHIRPath executable found but returned error: {FHIRPATH_EXE}")
            print(
                "   Query evaluation may fail, but questions and queries can still be generated"
            )
            return False

    except subprocess.TimeoutExpired:
        print(f"⚠️  FHIRPath executable timed out: {FHIRPATH_EXE}")
        print(
            "   Query evaluation may fail, but questions and queries can still be generated"
        )
        return False
    except FileNotFoundError:
        print(f"⚠️  FHIRPath executable not found: {FHIRPATH_EXE}")
        print(
            "   Query evaluation will be disabled, but questions and queries can still be generated"
        )
        return False
    except Exception as e:
        print(f"⚠️  Error testing FHIRPath executable: {e}")
        print(
            "   Query evaluation may fail, but questions and queries can still be generated"
        )
        return False


def test_valuesets():
    """Test that placeholder valuesets are present and properly loaded."""
    print("\nTesting placeholder valuesets...")

    try:
        from fhirpath_gen.valuesets import get_valueset, load_all_valuesets, VALUESETS

        # Test that valuesets directory exists and has files
        valuesets_dir = Path("fhirpath_gen/valuesets")
        if not valuesets_dir.exists():
            print("❌ Valuesets directory not found")
            return False

        # Check for required valueset files
        required_valuesets = [
            "drug_name.json",
            "procedure_name.json",
            "diagnosis_name.json",
            "lab_name.json",
            "vital_name.json",
            "patient_id.json",
            "admission_route.json",
            "careunit.json",
            "drug_route.json",
            "gender.json",
            "input_name.json",
            "output_name.json",
            "spec_name.json",
            "abbreviation.json",
        ]

        missing_files = []
        for filename in required_valuesets:
            filepath = valuesets_dir / filename
            if not filepath.exists():
                missing_files.append(filename)

        if missing_files:
            print(f"❌ Missing valueset files: {missing_files}")
            return False

        # Test that valuesets can be loaded
        try:
            all_valuesets = load_all_valuesets()
            print(f"✅ Loaded {len(all_valuesets)} valuesets")
        except Exception as e:
            print(f"❌ Failed to load valuesets: {e}")
            return False

        # Test specific valuesets that are commonly used
        test_valuesets = [
            "drug_name",
            "procedure_name",
            "diagnosis_name",
            "lab_name",
            "vital_name",
            "patient_id",
        ]

        for valueset_name in test_valuesets:
            try:
                values = get_valueset(valueset_name)
                if len(values) > 0:
                    print(f"✅ {valueset_name}: {len(values)} values")
                else:
                    print(f"⚠️  {valueset_name}: empty valueset")
            except Exception as e:
                print(f"❌ Failed to load {valueset_name}: {e}")
                return False

        # Test EHR-SQL valueset mapping
        try:
            mapping_file = valuesets_dir / "value_mapping" / "placeholder_values.json"
            if mapping_file.exists():
                with open(mapping_file, "r", encoding="utf-8") as f:
                    ehr_sql_values = json.load(f)
                print(f"✅ EHR-SQL valueset mapping: {len(ehr_sql_values)} entries")
            else:
                print("⚠️  EHR-SQL valueset mapping file not found")
        except Exception as e:
            print(f"⚠️  EHR-SQL valueset mapping error: {e}")

        return True

    except ImportError as e:
        print(f"❌ Failed to import valueset functions: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in valueset test: {e}")
        return False


def main():
    """Run all validation tests."""
    print("FHIRPath-QA Setup Validation")
    print("=" * 50)

    tests = [
        ("Dependencies", test_dependencies),
        ("Imports", test_imports),
        ("Valuesets", test_valuesets),
        ("Templates", test_templates),
        ("Patient Bundles", test_patient_bundles),
        ("Question Generation", test_question_generation),
        ("FHIRPath Executable", test_fhirpath_executable),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Your FHIR-QA setup is working correctly.")
        print("\nNext steps:")
        print("1. Read README.md (dataset overview + reproduction tutorial).")
        print("2. If reproducing datasets: set up HAPI + export patient bundles.")
        print("3. Try generation: python generate_questions.py --help")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the project root directory")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check that all valueset files are present in fhirpath_gen/valuesets/")
        print("4. Check README.md for setup and common fixes")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
