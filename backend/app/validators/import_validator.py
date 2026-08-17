"""AST üzerindeki import ifadelerini allowlist ile doğrular."""

import ast

ALLOWED_IMPORT_ROOTS = frozenset({"backtesting", "ta", "pandas", "numpy"})


def _root_module(module: str) -> str:
    return module.split(".", maxsplit=1)[0]


def validate_imports(tree: ast.Module) -> list[str]:
    """İzin verilmeyen veya göreli importlar için hata listesi döndür."""
    errors: list[str] = []
    rejected: set[str] = set()

    for node in ast.walk(tree):
        roots: list[str] = []

        if isinstance(node, ast.Import):
            roots = [_root_module(alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                roots = ["göreli import"]
            elif node.module:
                roots = [_root_module(node.module)]

        for root in roots:
            if root not in ALLOWED_IMPORT_ROOTS and root not in rejected:
                rejected.add(root)
                errors.append(f"İzin verilmeyen import: {root}")

    return errors
