"""AST üzerinde açıkça yasaklanmış fonksiyon çağrılarını bulur."""

import ast

FORBIDDEN_DIRECT_CALLS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "globals",
        "locals",
        "getattr",
        "setattr",
        "delattr",
        "__import__",
        "print",
    }
)
FORBIDDEN_ATTRIBUTE_CALLS = frozenset(
    {"os.system", "subprocess.run", "subprocess.Popen"}
)


class SecurityVisitor(ast.NodeVisitor):
    """Yasaklı doğrudan ve açık attribute çağrılarını toplar."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self._reported: set[str] = set()

    def _report(self, call_name: str) -> None:
        if call_name not in self._reported:
            self._reported.add(call_name)
            self.errors.append(f"Yasaklı fonksiyon çağrısı: {call_name}")

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_DIRECT_CALLS:
            self._report(node.func.id)
        elif (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ):
            qualified_name = f"{node.func.value.id}.{node.func.attr}"
            if qualified_name in FORBIDDEN_ATTRIBUTE_CALLS:
                self._report(qualified_name)

        self.generic_visit(node)


def validate_security(tree: ast.Module) -> list[str]:
    """Yasaklı çağrılar için hata listesi döndür."""
    visitor = SecurityVisitor()
    visitor.visit(tree)
    return visitor.errors
