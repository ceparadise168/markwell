def test_package_imports_with_version():
    import kobo_backup
    assert kobo_backup.__version__ == "0.1.0"
