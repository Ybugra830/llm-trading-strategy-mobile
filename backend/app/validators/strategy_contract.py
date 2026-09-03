"""Conservative, non-executing Position/Trade and percentage-trailing contract."""
from __future__ import annotations

import ast
import copy
import math
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractFinding:
    code: str
    message: str
    family: str = "position_management"


@dataclass(frozen=True)
class StrategyRequirements:
    trailing_requested: bool = False
    trailing_fraction: float | None = None


@dataclass(frozen=True)
class ContractAnalysis:
    requirements: StrategyRequirements
    findings: tuple[ContractFinding, ...]


MESSAGES = {
    "invalid_position_attribute": "Invalid position attribute: Position.entry_price is unavailable; Position supports truthiness and close() only.",
    "invalid_trade_attribute": "Invalid Trade API: only entry_price (read) and sl (read/write) are supported.",
    "unsupported_object_access": "Unsupported Position/Trade access: use self.position only in conditions or close(), and iterate for trade in self.trades in next(). Do not alias, index, rebind or pass these objects elsewhere.",
    "long_only_exit": "Long-only contract: use self.position.close(), never self.sell().",
    "invalid_trailing_percentage": "A trailing stop requires one unambiguous numeric percentage strictly between 0 and 100.",
    "invalid_trailing_implementation": "Invalid trailing stop: at the start of next(), iterate all self.trades and assign trade.sl = max(trade.sl or trade.entry_price * (1 - p), self.data.High[-1] * (1 - p)), using the requested percentage. Fixed, conditional, decreasing or unprovable stops are unsupported.",
}

PROTECTED_STRATEGY_MEMBERS = frozenset({"data", "position", "trades", "closed_trades", "orders", "buy", "sell", "I"})


def parse_requirements(prompt: str | None) -> tuple[StrategyRequirements, list[ContractFinding]]:
    normalized = "".join(c for c in unicodedata.normalize("NFKD", (prompt or "").casefold())
                         if not unicodedata.combining(c))
    requested = bool(re.search(r"\btrailing\b|iz\s*suren|takip\s*eden\s*(?:stop|zarar)|hareketli\s*(?:stop|zarar)", normalized))
    if not requested:
        return StrategyRequirements(), []
    numeric = r"[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)"
    # Do not silently read the tail of an unsupported number, e.g. 2e2% as 2%.
    matches = re.findall(
        rf"(?:%|\byuzde\b)\s*({numeric})(?![\w.,+-])|(?<![\w.,+-])({numeric})\s*(?:%|percent\b|yuzde\b)",
        normalized,
    )
    percentages = {float((a or b).replace(",", ".")) for a, b in matches}
    if len(percentages) != 1 or not 0 < next(iter(percentages), 0) < 100:
        return StrategyRequirements(True), [ContractFinding("invalid_trailing_percentage", MESSAGES["invalid_trailing_percentage"])]
    return StrategyRequirements(True, percentages.pop() / 100), []


def path(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = path(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


class ApiVisitor(ast.NodeVisitor):
    def __init__(self, tree: ast.Module):
        self.parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        self.findings: dict[str, ContractFinding] = {}
        self.trades: set[str] = set()
        self.function = ""
        self.trade_names = {n.target.id for n in ast.walk(tree) if isinstance(n, ast.For)
                            and path(n.iter) == "self.trades" and isinstance(n.target, ast.Name)}

    def reject(self, code: str):
        self.findings[code] = ContractFinding(code, MESSAGES[code])

    def visit_FunctionDef(self, node):
        if node.name in PROTECTED_STRATEGY_MEMBERS or node.name in ("__init__", "__getattr__", "__getattribute__", "__setattr__", "GeneratedStrategy"):
            self.reject("unsupported_object_access")
        old_function, old_trades = self.function, self.trades
        self.function, self.trades = node.name, set()
        self.generic_visit(node)
        self.function, self.trades = old_function, old_trades

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        for statement in node.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if any(isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))
                       and n.id in PROTECTED_STRATEGY_MEMBERS | {"next", "init"} for n in ast.walk(statement)):
                    self.reject("unsupported_object_access")
        self.generic_visit(node)

    def visit_For(self, node):
        if path(node.iter) == "self.trades" and isinstance(node.target, ast.Name):
            if self.function != "next":
                self.reject("unsupported_object_access")
            old = self.trades.copy()
            self.trades.add(node.target.id)
            self.generic_visit(node)
            self.trades = old
        else:
            self.generic_visit(node)

    def condition_use(self, node):
        parent = self.parents.get(node)
        while isinstance(parent, (ast.BoolOp, ast.UnaryOp)):
            node, parent = parent, self.parents.get(parent)
        return isinstance(parent, (ast.If, ast.IfExp, ast.While)) and parent.test is node

    def visit_Name(self, node):
        if node.id == "GeneratedStrategy" and not isinstance(node.ctx, ast.Load):
            self.reject("unsupported_object_access")
        if node.id == "self":
            parent = self.parents.get(node)
            if not isinstance(node.ctx, ast.Load) or not isinstance(parent, ast.Attribute) or parent.value is not node:
                self.reject("unsupported_object_access")
        if node.id in self.trade_names and node.id not in self.trades:
            self.reject("unsupported_object_access")
        if node.id in self.trades:
            parent = self.parents.get(node)
            valid_target = isinstance(parent, ast.For) and parent.target is node and path(parent.iter) == "self.trades"
            valid_read = isinstance(parent, ast.Attribute) and parent.value is node and isinstance(node.ctx, ast.Load)
            if not (valid_target or valid_read):
                self.reject("unsupported_object_access")

    def visit_Attribute(self, node):
        value = path(node)
        parent = self.parents.get(node)
        if not isinstance(node.ctx, ast.Load) and node.attr in PROTECTED_STRATEGY_MEMBERS | {"next", "init"}:
            self.reject("unsupported_object_access")
        if node.attr.startswith("_") or value in ("self.closed_trades", "self.orders"):
            self.reject("unsupported_object_access")
        if node.attr in ("position", "trades") and value not in ("self.position", "self.trades"):
            self.reject("unsupported_object_access")
        if node.attr in ("entry_price", "sl") and not (isinstance(node.value, ast.Name) and node.value.id in self.trades):
            self.reject("invalid_trade_attribute")
        if value == "self.sell":
            self.reject("long_only_exit")
        if value == "self.position":
            close = isinstance(parent, ast.Attribute) and parent.attr == "close" and isinstance(node.ctx, ast.Load)
            if not close and not self.condition_use(node):
                self.reject("unsupported_object_access")
        elif value and value.startswith("self.position."):
            if value != "self.position.close" or not isinstance(parent, ast.Call) or parent.func is not node or parent.args or parent.keywords:
                self.reject("invalid_position_attribute")
        elif value == "self.trades":
            if not isinstance(parent, ast.For) or parent.iter is not node or not isinstance(node.ctx, ast.Load):
                self.reject("unsupported_object_access")
        if isinstance(node.value, ast.Name) and node.value.id in self.trades:
            if node.attr not in ("entry_price", "sl") or isinstance(node.ctx, ast.Del) or (node.attr == "entry_price" and not isinstance(node.ctx, ast.Load)):
                self.reject("invalid_trade_attribute")
            if isinstance(parent, ast.Call) and parent.func is node:
                self.reject("invalid_trade_attribute")
        self.generic_visit(node)


def resolve(node: ast.AST, env: dict[str, ast.AST], seen=frozenset()) -> ast.AST:
    key = path(node)
    if key in env and key not in seen:
        return resolve(env[key], env, seen | {key})
    return node


def snapshot(node: ast.AST, env: dict[str, ast.AST]) -> ast.AST:
    """Freeze an alias at assignment time; later rebinding must not rewrite history."""
    class Expand(ast.NodeTransformer):
        def visit(self, value):
            key = path(value)
            if key in env:
                return copy.deepcopy(env[key])
            return super().visit(value)
    return Expand().visit(copy.deepcopy(node))


def number(node: ast.AST, env: dict[str, ast.AST], depth=0) -> float | None:
    if depth > 20:
        return None
    node = resolve(node, env)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        try:
            value = float(node.value)
            return value if math.isfinite(value) else None
        except OverflowError:
            return None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = number(node.operand, env, depth + 1)
        return None if value is None else (-value if isinstance(node.op, ast.USub) else value)
    if isinstance(node, ast.BinOp):
        left, right = number(node.left, env, depth + 1), number(node.right, env, depth + 1)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Sub): return left - right
        if isinstance(node.op, ast.Add): return left + right
        if isinstance(node.op, ast.Mult): return left * right
        if isinstance(node.op, ast.Div) and right: return left / right
    return None


def pure_alias(node: ast.AST, env: dict[str, ast.AST], trade: str | None = None, depth=0) -> bool:
    if depth > 20:
        return False
    node = resolve(node, env)
    if number(node, env) is not None:
        return True
    if path(node) in (f"{trade}.sl", f"{trade}.entry_price") and trade:
        return True
    if isinstance(node, ast.Subscript):
        return path(node.value) == "self.data.High" and number(node.slice, env) == -1
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Sub, ast.Add, ast.Div)):
        return pure_alias(node.left, env, trade, depth + 1) and pure_alias(node.right, env, trade, depth + 1)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return all(pure_alias(v, env, trade, depth + 1) for v in node.values)
    if isinstance(node, ast.Call) and path(node.func) == "max" and not node.keywords:
        return all(pure_alias(v, env, trade, depth + 1) for v in node.args)
    return False


def valid_stop(node: ast.AST, trade: str, fraction: float, env: dict[str, ast.AST]) -> bool:
    def scaled(expr, expected_path):
        expr = resolve(expr, env)
        if not isinstance(expr, ast.BinOp) or not isinstance(expr.op, ast.Mult):
            return False
        for base, factor in ((expr.left, expr.right), (expr.right, expr.left)):
            base = resolve(base, env)
            coefficient = number(factor, env)
            correct_base = path(base) == expected_path
            if expected_path == "HIGH":
                correct_base = isinstance(base, ast.Subscript) and path(base.value) == "self.data.High" and number(base.slice, env) == -1
            if correct_base and coefficient is not None and math.isclose(coefficient, 1 - fraction, abs_tol=1e-10, rel_tol=0):
                return True
        return False

    def baseline(expr):
        expr = resolve(expr, env)
        return (isinstance(expr, ast.BoolOp) and isinstance(expr.op, ast.Or) and len(expr.values) == 2
                and path(resolve(expr.values[0], env)) == f"{trade}.sl"
                and scaled(expr.values[1], f"{trade}.entry_price"))

    node = resolve(node, env)
    if not isinstance(node, ast.Call) or path(node.func) != "max" or node.keywords or len(node.args) != 2:
        return False
    return any(baseline(a) and scaled(b, "HIGH") for a, b in (node.args, node.args[::-1]))


def trailing_proven(tree: ast.Module, fraction: float) -> bool:
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "GeneratedStrategy"]
    if len(classes) != 1:
        return False
    cls = classes[0]
    nexts = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "next"]
    if len(nexts) != 1 or nexts[0].decorator_list or cls.decorator_list:
        return False
    args = nexts[0].args
    if ([a.arg for a in args.posonlyargs + args.args] != ["self"] or args.defaults
            or args.kwonlyargs or args.vararg or args.kwarg):
        return False
    if any(isinstance(n, (ast.Yield, ast.YieldFrom, ast.Await)) for n in ast.walk(nexts[0])):
        return False
    if any(isinstance(n, (ast.Assign, ast.AnnAssign)) and
           any(isinstance(x, ast.Name) and x.id in ("next", "data", "trades", "position")
               and isinstance(x.ctx, ast.Store) for x in ast.walk(n)) for n in cls.body):
        return False
    # Shadowing the trusted builtin or overriding data/entrypoints makes the proof invalid.
    for n in ast.walk(tree):
        if isinstance(n, (ast.Global, ast.Nonlocal)):
            return False
        if isinstance(n, ast.Name) and n.id == "max" and isinstance(n.ctx, (ast.Store, ast.Del)):
            return False
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.name == "max":
            return False
        if isinstance(n, ast.arg) and n.arg == "max":
            return False
        if isinstance(n, ast.alias) and (n.asname or n.name.split(".")[0]) in ("max", "*"):
            return False
        if isinstance(n, ast.Attribute) and not isinstance(n.ctx, ast.Load):
            target = path(n) or ""
            if target in ("self.data", "self.next", "GeneratedStrategy.next") or target.startswith("self.data."):
                return False

    env: dict[str, ast.AST] = {}
    for owner, prefix in ((tree, ""), (cls, "self.")):
        for n in owner.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and number(n.value, env) is not None:
                name = prefix + n.targets[0].id
                # Function/class/import bindings do not have ast.Store contexts.
                local_name = n.targets[0].id
                if any((isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and x.name == local_name)
                       or (isinstance(x, ast.alias) and (x.asname or x.name.split('.')[0]) == local_name)
                       for x in ast.walk(owner)):
                    continue
                if prefix and sum(isinstance(x, ast.Name) and x.id == local_name and isinstance(x.ctx, (ast.Store, ast.Del))
                                  for statement in cls.body if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                                  for x in ast.walk(statement)) != 1:
                    continue
                # Do not treat a mutable global/class parameter as a compile-time constant.
                stores = sum((path(x) == name or (bool(prefix) and path(x) == "GeneratedStrategy." + n.targets[0].id))
                             and isinstance(getattr(x, "ctx", None), (ast.Store, ast.Del))
                             for x in ast.walk(tree))
                if stores == (0 if prefix else 1):
                    env[name] = ast.Constant(number(n.value, env))

    matched = None
    next_method = nexts[0]
    for statement in next_method.body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
            continue
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name) and pure_alias(statement.value, env):
            env[statement.targets[0].id] = snapshot(statement.value, env)
            continue
        if not isinstance(statement, ast.For) or path(statement.iter) != "self.trades" or not isinstance(statement.target, ast.Name) or statement.orelse:
            return False
        trade = statement.target.id
        loop_env = env.copy()
        for inner in statement.body:
            if isinstance(inner, ast.Assign) and len(inner.targets) == 1:
                target = inner.targets[0]
                if isinstance(target, ast.Name) and target.id != trade and pure_alias(inner.value, loop_env, trade):
                    loop_env[target.id] = snapshot(inner.value, loop_env)
                elif path(target) == f"{trade}.sl" and matched is None and valid_stop(inner.value, trade, fraction, loop_env):
                    matched = target
                else:
                    return False
            else:
                return False
        if matched is None:
            return False
        break
    if matched is None:
        return False
    # Reject later resets/alternate stop writes, and overrides through the class API.
    writes = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "sl" and not isinstance(n.ctx, ast.Load)]
    return writes == [matched]


def analyze_contract(code: str, prompt: str | None = None) -> ContractAnalysis:
    requirements, findings = parse_requirements(prompt)
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return ContractAnalysis(requirements, tuple(findings))
    visitor = ApiVisitor(tree)
    visitor.visit(tree)
    findings.extend(visitor.findings.values())
    if requirements.trailing_requested and requirements.trailing_fraction is not None:
        if not trailing_proven(tree, requirements.trailing_fraction):
            findings.append(ContractFinding("invalid_trailing_implementation", MESSAGES["invalid_trailing_implementation"]))
    return ContractAnalysis(requirements, tuple(findings))
