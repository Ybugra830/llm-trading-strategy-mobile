"""Açık negatif pandas shift kullanımlarını statik olarak işaretler."""

import ast

LOOKAHEAD_ERROR = "Gelecek veriye erişim şüphesi: negatif shift kullanımı."


def _is_negative_literal(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
        and not isinstance(node.operand.value, bool)
        and node.operand.value > 0
    )


class LookaheadVisitor(ast.NodeVisitor):
    """Doğrudan ``.shift(-N)`` çağrılarını tespit eder."""

    def __init__(self) -> None:
        self.detected = False

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and node.func.attr == "shift":
            positional_period = node.args[0] if node.args else None
            keyword_period = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "periods"),
                None,
            )
            if (
                positional_period is not None
                and _is_negative_literal(positional_period)
            ) or (
                keyword_period is not None and _is_negative_literal(keyword_period)
            ):
                self.detected = True

        self.generic_visit(node)


def validate_lookahead(tree: ast.Module) -> list[str]:
    """Basit negatif shift kalıbı bulunursa tek bir hata döndür."""
    visitor = LookaheadVisitor()
    visitor.visit(tree)
    return [LOOKAHEAD_ERROR] if visitor.detected else []
