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


# this is the best way to share utility functions with test modules i
# found, it looks like java but it works
class Utils:

    @contextlib.contextmanager
    def error_at(self, *location_args, msg=None):
        with pytest.raises(weirdc.CompileError) as err:
            yield

        if msg is not None:
            assert err.value.message == msg
        assert err.value.location == weirdc.Location(*location_args)


@pytest.fixture
def utils():
    return Utils()
