"""disktools — cross-platform disk-maintenance suite (Opsi A: Python unified).

One codebase, OS detected at runtime (see `platform_probe`), dispatching to the
matching backend: `platform_windows` or `platform_linux`. The concepts/altitude
are identical to the original bash suite — only the "machine" underneath changes.
"""

__version__ = "0.1.0"
