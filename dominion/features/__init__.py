"""HYDRA C++ feature kernels bridge."""
try:
    from .hydra_kernels import *  # noqa: F401, F403
    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False
