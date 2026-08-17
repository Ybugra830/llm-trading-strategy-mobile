"""GeneratedStrategy sınıf sözleşmesini AST üzerinden doğrular."""

import ast


def _is_strategy_base(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id == "Strategy"
    return (
        isinstance(base, ast.Attribute)
        and base.attr == "Strategy"
        and isinstance(base.value, ast.Name)
        and base.value.id == "backtesting"
    )


def validate_interface(tree: ast.Module) -> list[str]:
    """GeneratedStrategy inheritance ve metot gereksinimlerini doğrula."""
    strategy_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "GeneratedStrategy"
        ),
        None,
    )
    if strategy_class is None:
        return ["GeneratedStrategy sınıfı bulunamadı."]

    errors: list[str] = []
    if not any(_is_strategy_base(base) for base in strategy_class.bases):
        errors.append("GeneratedStrategy, Strategy sınıfından türemelidir.")

    method_names = {
        node.name for node in strategy_class.body if isinstance(node, ast.FunctionDef)
    }
    if "init" not in method_names:
        errors.append("GeneratedStrategy.init() metodu bulunamadı.")
    if "next" not in method_names:
        errors.append("GeneratedStrategy.next() metodu bulunamadı.")

    return errors
