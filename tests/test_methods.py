import logging
import unittest

from openbaton.main import ImageGenerator


class MyTestCase(unittest.TestCase):
    def test_method(self):
        own_cfg = {

            'destination': '/tmp/destimgtest',
            'tempdir': '/tmp/tempdir',
        }
        kwargs = {
            'filename': '/tmp/test.tar.gz',
        }
        img = ImageGenerator(logging.getLogger("img.gen.test"), {}, {})
        img.do_clean(own_config=own_cfg, **kwargs)


if __name__ == '__main__':
    unittest.main()
