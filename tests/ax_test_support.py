#!/usr/bin/env python3
"""Scrub store-redirecting environment variables for the whole test run.

`ax` reads a few environment variables at call time (e.g. HERMES_HOME) so
wrapper environments can relocate provider stores. When a test run happens
inside such a wrapper (an agent session, a CI job with custom env), those
variables point away from tests/fixtures/ and fixture-based tests silently
see real session data (issue #31).

Usage: every test module imports this BEFORE creating its ax module
instance (i.e. before load_ax / setUpClass runs):

    import ax_test_support  # noqa: F401  (scrubs HERMES_HOME on import)

The scrub is process-wide and one-shot at import time: removed variables
are not restored, so nothing leaks past the test process either. A test
that deliberately sets a scrubbed variable must save/restore it itself and
may call importlib.reload(ax_test_support) to re-scrub.
"""

import os
import sys

SCRUBBED = ("HERMES_HOME",)

_scrubbed = [n for n in SCRUBBED if n in os.environ]
for _name in _scrubbed:
    del os.environ[_name]
if _scrubbed:
    print("ax_test_support: scrubbed %s" % ", ".join(_scrubbed),
          file=sys.stderr)
