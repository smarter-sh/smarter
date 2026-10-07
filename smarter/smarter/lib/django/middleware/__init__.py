"""
Smarter Middleware classes.
"""

from .cors import SmarterCorsMiddleware
from .csrf import SmarterCsrfViewMiddleware
from .excessive_404 import SmarterBlockExcessive404Middleware
from .html_minify import HTMLMinifyMiddleware
from .json import SmarterJsonErrorMiddleware
from .sensitive_files import SmarterBlockSensitiveFilesMiddleware

__all__ = [
    "SmarterCorsMiddleware",
    "SmarterCsrfViewMiddleware",
    "SmarterBlockSensitiveFilesMiddleware",
    "SmarterBlockExcessive404Middleware",
    "HTMLMinifyMiddleware",
    "SmarterJsonErrorMiddleware",
]
