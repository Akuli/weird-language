import contextlib

import pytest

try:
    import weirdc
except ImportError:
    import sys
    from os.path import dirname, abspath
    project_root = dirname(dirname(abspath(__file__)))
    sys.path.append(project_root)
    import weirdc


@pytest.fixture
def error_at():
    @contextlib.contextmanager
    def inner(*location_args, msg=None):
        if location_args == (None,):
            location = None
        else:
            location = weirdc.Location(*location_args)

        with pytest.raises(weirdc.CompileError) as err:
            yield

        if msg is not None:
            assert err.value.message == msg
        assert err.value.location == location

    return inner
