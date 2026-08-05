"""
Security policy constants for the local sandbox.

The validator references these sets to statically reject code that tries to
escape the sandbox (via imports) or execute dynamic code (eval/exec/compile).
Keeping every policy in one module makes the whole sandbox easy to audit
and extend: adding a forbidden name here is enough to enforce it.
"""

BLOCKED_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "subprocess",
        "socket",
        "shutil",
        "multiprocessing",
        "pathlib",
        "importlib",
        "ctypes",
    }
)
"""
Top-level modules a snippet is not allowed to import.

``importlib`` and ``ctypes`` are included beyond the core list because
``importlib.import_module`` can pull in any of the others and ``ctypes``
allows arbitrary low-level memory access. Submodules (e.g. ``os.path``)
are blocked implicitly by the validator's top-level check.
"""

DANGEROUS_FUNCTIONS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
    }
)
"""
Callables that execute or compile strings as code and are therefore able to
bypass the static import checks.
"""
