# Smarter lib

This folder contains extensions to third party code used in the project. Rather than subclass these packages, we prefer
to import the original package here, and then create our additional/modified code such that it is importable via `smarter.lib.`.
For example, we've made enhancements to Python's `json` library, which is imported across the project as follows:

```python
from smarter.lib import json
```
