try:
    import weirdc
except ImportError:
    import sys
    from os.path import dirname, abspath
    project_root = dirname(dirname(abspath(__file__)))
    sys.path.append(project_root)
    import weirdc
