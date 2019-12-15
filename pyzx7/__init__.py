import ctypes
import os
import glob
from ctypes.util import find_library
libpath = os.path.dirname(__file__)
libfile = glob.glob(os.path.join(libpath, 'zx7*'))[0]

# find the shared library, the path depends on the platform and Python version
print("Loading {}".format(libfile))
zx7_lib = ctypes.cdll.LoadLibrary(libfile)

zx7_lib.comp.restype = ctypes.c_int
zx7_lib.comp.argtypes = (ctypes.c_char_p,)


def compress(filename):
    try:
        filename = filename.encode('utf-8')
    except:
        pass

    zx7_lib.comp(filename)

