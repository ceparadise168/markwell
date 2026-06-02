def test_package_imports_with_version():
    import markwell
    assert markwell.__version__ == "0.1.0"


def test_desktop_entrypoint_imports():
    from markwell import desktop
    assert callable(desktop.main)
