"""Non-executing capability checks with conservative lexical alias analysis."""

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

PANDAS_WRITERS = frozenset({
    "to_csv", "to_json", "to_pickle", "to_excel", "to_parquet", "to_feather",
    "to_hdf", "to_sql", "to_xml", "to_html", "to_latex", "to_markdown",
    "to_stata", "to_orc", "to_gbq", "to_clipboard",
})
NUMPY_IO = frozenset({
    "load", "save", "savez", "savez_compressed", "loadtxt", "savetxt",
    "genfromtxt", "fromfile", "memmap", "DataSource", "open_memmap",
    "tofile", "dump",
})
PATH_IO = frozenset({
    "open", "read_text", "read_bytes", "write_text", "write_bytes", "touch",
    "mkdir", "rmdir", "unlink", "rename", "replace", "chmod", "lchmod",
    "symlink_to", "hardlink_to", "link_to", "stat", "lstat", "exists",
    "is_file", "is_dir", "is_symlink", "is_mount", "is_socket", "is_fifo",
    "is_block_device", "is_char_device", "iterdir", "glob", "rglob", "walk",
    "resolve", "absolute", "owner", "group", "samefile", "cwd", "home",
    "expanduser", "readlink", "copy", "copy_into", "move", "move_into",
})


class _Scope:
    def __init__(self, parent=None, *, is_class=False):
        self.parent = parent
        self.is_class = is_class
        self.bindings: dict[str, set[str]] = {}

    def lookup(self, name: str) -> set[str]:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        # Preserve the existing lexical rejection of forbidden direct names.
        return {name} if name in FORBIDDEN_DIRECT_CALLS | {"os", "subprocess"} else set()


class _Bindings(ast.NodeVisitor):
    """Collect lexical facts, then union origins to a fixed point.

    Binding sets deliberately never discard origins on reassignment. This makes
    branches, loops and late module bindings fail closed without executing code
    or pretending to prove control flow. Scopes prevent unrelated locals from
    contaminating one another. Origins have bounded depth to terminate cycles.
    """

    def __init__(self, tree: ast.Module):
        self.scope = _Scope()
        self.scopes: dict[ast.AST, _Scope] = {}
        self.class_scopes: dict[ast.AST, _Scope | None] = {}
        self.facts: list[tuple[_Scope, str, ast.AST]] = []
        self.functions: dict[str, tuple[_Scope, ast.arguments]] = {}
        self.calls: list[ast.Call] = []
        self.class_scope = None
        self.function_scope = None
        self.visit(tree)
        changed = True
        while changed:
            changed = False
            for scope, name, value in self.facts:
                before = len(scope.bindings[name])
                scope.bindings[name].update(self.origins(value))
                changed |= len(scope.bindings[name]) != before
            for call in self.calls:
                for origin in self.origins(call.func):
                    if origin not in self.functions:
                        continue
                    scope, args = self.functions[origin]
                    supplied = list(zip(args.posonlyargs + args.args, call.args))
                    names = {arg.arg: arg for arg in args.posonlyargs + args.args + args.kwonlyargs}
                    supplied.extend((names[k.arg], k.value) for k in call.keywords if k.arg in names)
                    for arg, value in supplied:
                        before = len(scope.bindings[arg.arg])
                        scope.bindings[arg.arg].update(self.origins(value))
                        changed |= len(scope.bindings[arg.arg]) != before

    def visit(self, node):
        self.scopes[node] = self.scope
        self.class_scopes[node] = self.class_scope
        return super().visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            origin = alias.name if alias.asname else name
            self.scope.bindings.setdefault(name, set()).add(origin)

    def visit_ImportFrom(self, node):
        if node.module and not node.level:
            for alias in node.names:
                self.scope.bindings.setdefault(alias.asname or alias.name, set()).add(
                    f"{node.module}.{alias.name}"
                )

    def bind(self, target, value):
        if isinstance(target, ast.Name):
            self.scope.bindings.setdefault(target.id, set())
            self.facts.append((self.scope, target.id, value))
        elif (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
              and target.value.id == "self" and self.class_scope is not None):
            name = f"self.{target.attr}"
            self.class_scope.bindings.setdefault(name, set())
            self.facts.append((self.class_scope, name, value))
        elif isinstance(target, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(target.elts) == len(value.elts):
                for left, right in zip(target.elts, value.elts):
                    self.bind(left, right)

    def visit_Assign(self, node):
        for target in node.targets:
            self.bind(target, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.bind(node.target, node.value)
        self.generic_visit(node)

    def visit_NamedExpr(self, node):
        self.bind(node.target, node.value)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        token = f"function:{id(node)}"
        self.scope.bindings.setdefault(node.name, set()).add(token)
        if self.scope.is_class:
            self.scope.bindings.setdefault(f"self.{node.name}", set()).add(token)
        # Defaults and decorators are evaluated in the enclosing scope.
        for value in node.decorator_list + node.args.defaults + [v for v in node.args.kw_defaults if v]:
            self.visit(value)
        outer = self.scope
        old_function = self.function_scope
        # Python methods do not close over class-body local variables.
        self.scope = _Scope(outer.parent if outer.is_class else outer)
        self.function_scope = self.scope
        self.functions[token] = (self.scope, node.args)
        self.scope.bindings["$return"] = set()
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            self.scope.bindings[arg.arg] = set()
        for arg in (node.args.vararg, node.args.kwarg):
            if arg:
                self.scope.bindings[arg.arg] = set()
        positional = node.args.posonlyargs + node.args.args
        for arg, value in zip(positional[len(positional) - len(node.args.defaults):], node.args.defaults):
            self.facts.append((self.scope, arg.arg, value))
        for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults):
            if value is not None:
                self.facts.append((self.scope, arg.arg, value))
        for statement in node.body:
            self.visit(statement)
        self.scope = outer
        self.function_scope = old_function

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        token = f"function:{id(node)}"
        outer = self.scope
        for value in node.args.defaults + [v for v in node.args.kw_defaults if v]:
            self.visit(value)
        self.scope = _Scope(outer)
        self.functions[token] = (self.scope, node.args)
        self.scope.bindings["$return"] = set()
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            self.scope.bindings[arg.arg] = set()
        for arg in (node.args.vararg, node.args.kwarg):
            if arg:
                self.scope.bindings[arg.arg] = set()
        positional = node.args.posonlyargs + node.args.args
        for arg, value in zip(positional[len(positional) - len(node.args.defaults):], node.args.defaults):
            self.facts.append((self.scope, arg.arg, value))
        for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults):
            if value is not None:
                self.facts.append((self.scope, arg.arg, value))
        self.facts.append((self.scope, "$return", node.body))
        self.visit(node.body)
        self.scope = outer

    def visit_Call(self, node):
        self.calls.append(node)
        self.generic_visit(node)

    def visit_Return(self, node):
        if node.value is not None and self.function_scope is not None:
            self.facts.append((self.function_scope, "$return", node.value))
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.scope.bindings.setdefault(node.name, set())
        for value in node.bases + node.decorator_list:
            self.visit(value)
        outer = self.scope
        old_class = self.class_scope
        self.scope = _Scope(outer, is_class=True)
        self.class_scope = self.scope
        for statement in node.body:
            self.visit(statement)
        self.scope = outer
        self.class_scope = old_class

    def origins(self, node: ast.AST) -> set[str]:
        scope = self.scopes.get(node, self.scope)
        if isinstance(node, ast.Name):
            return scope.lookup(node.id)
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                if node.attr == "data":
                    return {"backtesting.Data"}
                owner = self.class_scopes.get(node)
                return owner.bindings.get(f"self.{node.attr}", set()) if owner else set()
            result = set()
            for base in self.origins(node.value):
                # Preserve public array/dataframe conversion provenance.
                if base == "backtesting.Data":
                    result.add("pandas.DataFrame" if node.attr == "df" else "backtesting.Array")
                elif base == "backtesting.Array":
                    if node.attr in {"s", "df"}:
                        result.add("pandas.Series" if node.attr == "s" else "pandas.DataFrame")
                    else:
                        result.add(f"numpy.ndarray.{node.attr}")
                elif base.startswith("pandas.") and node.attr in {"values", "array"}:
                    result.add("numpy.ndarray")
                elif base.count(".") < 8:
                    result.add(f"{base}.{node.attr}")
                else:
                    result.add("unresolved_capability_depth")
            return result
        if isinstance(node, ast.Lambda):
            return {f"function:{id(node)}"}
        if isinstance(node, ast.Call):
            result = set()
            for origin in self.origins(node.func):
                if origin in self.functions:
                    result.update(self.functions[origin][0].bindings["$return"])
                    continue
                root = origin.split(".")[0]
                if root == "pandas":
                    if origin.endswith(".to_numpy"):
                        result.add("numpy.ndarray")
                    else:
                        kind = "Series" if origin == "pandas.Series" else "DataFrame"
                        result.add(f"pandas.{kind}")
                elif root == "numpy":
                    result.add("numpy.ndarray")
                elif root == "pathlib":
                    result.add("pathlib.Path")
            return result
        if isinstance(node, ast.Subscript):
            return self.origins(node.value)
        if isinstance(node, ast.NamedExpr):
            return self.origins(node.value)
        if isinstance(node, ast.IfExp):
            return self.origins(node.body) | self.origins(node.orelse)
        if isinstance(node, ast.BinOp):
            return self.origins(node.left) | self.origins(node.right)
        if isinstance(node, ast.BoolOp):
            return set().union(*(self.origins(value) for value in node.values))
        return set()


def _forbidden_origin(origin: str) -> str | None:
    if origin == "unresolved_capability_depth" or origin.startswith("unresolved_capability_depth."):
        return "unresolved_capability_depth"
    if origin in FORBIDDEN_DIRECT_CALLS | FORBIDDEN_ATTRIBUTE_CALLS:
        return origin
    parts = origin.split(".")
    root, member = parts[0], parts[-1]
    if root == "builtins" and member in FORBIDDEN_DIRECT_CALLS:
        return member
    if root == "pandas":
        if member.startswith("read_") or member in {"ExcelFile", "ExcelWriter", "HDFStore", "*"}:
            return f"pandas.{member}"
        if member in PANDAS_WRITERS:
            return f"pandas.{member}"
    if root == "numpy" and (member in NUMPY_IO or member == "*"):
        return f"numpy.{member}"
    if root == "pathlib" and (member in PATH_IO or member in {"Path", "PosixPath", "WindowsPath"}):
        return f"pathlib.Path.{member}" if member in PATH_IO else "pathlib.Path"
    return None


class SecurityVisitor(ast.NodeVisitor):
    """Yasaklı doğrudan ve açık attribute çağrılarını toplar."""

    def __init__(self, bindings: _Bindings) -> None:
        self.errors: list[str] = []
        self._reported: set[str] = set()
        self.bindings = bindings

    def _report(self, call_name: str) -> None:
        if call_name not in self._reported:
            self._reported.add(call_name)
            self.errors.append(f"Yasaklı fonksiyon çağrısı: {call_name}")

    def visit(self, node):
        if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_DIRECT_CALLS:
                self._report(node.id)
            for origin in sorted(self.bindings.origins(node)):
                forbidden = _forbidden_origin(origin)
                if forbidden:
                    self._report(forbidden)
        return super().visit(node)

    def visit_ImportFrom(self, node):
        if node.module and not node.level:
            for alias in node.names:
                forbidden = _forbidden_origin(f"{node.module}.{alias.name}")
                if forbidden:
                    self._report(forbidden)


def validate_security(tree: ast.Module) -> list[str]:
    """Yasaklı çağrılar için hata listesi döndür."""
    visitor = SecurityVisitor(_Bindings(tree))
    visitor.visit(tree)
    return visitor.errors
