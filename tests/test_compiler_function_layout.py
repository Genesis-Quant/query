"""Operator helpers belong to common; query execution keeps its existing layout."""

import ast
import importlib
import re
from pathlib import Path
from typing import get_args

import pytest

from query import Derivative, compile
from query.database.compile import DolphinDBFunction, collect_functions
from query.database.compile.common import functions as common_functions
from query.database.compile.common.functions import COMMON_FUNCTIONS
from query.database.compile.query import functions as query_functions
from query.database.compile.query.functions import OPERATOR_FUNCTIONS, QUERY_FUNCTIONS


@pytest.mark.parametrize("name,category,prefix,registry", [
    ("direct", "DIRECT", "direct_", "DIRECT_OPERATOR_FUNCTIONS"),
    ("time_series", "TS", "ts_", "TIME_SERIES_OPERATOR_FUNCTIONS"),
    ("cross_section", "CS", "cs_", "CROSS_SECTION_OPERATOR_FUNCTIONS"),
])
def test_operator_files_define_exactly_registered_operators(name, category, prefix, registry):
    module = importlib.import_module("query.database.compile.query.functions." + name)
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "DolphinDBFunction"
    ]
    definitions = [getattr(module, node.targets[0].id) for node in assignments]
    registered = getattr(module, registry)
    assert definitions
    assert {id(function) for function in definitions} == {id(function) for function in registered}
    expected = {
        prefix + operation.replace(".", "_"): model
        for operation, model in Derivative.operators.items()
        if get_args(model.model_fields["type"].annotation) == (category,)
    }
    assert {function.name for function in definitions} == set(expected)
    for function in definitions:
        assert function.module == "query"
        model = expected[function.name]
        fields = list(model.model_fields["fields"].annotation.model_fields)
        if function.name.startswith("cs_grouped_"):
            fields.remove("by")
        params = list(model.model_fields["params"].annotation.model_fields)
        assert function.parameters == tuple(fields + params)
        dependencies = collect_functions(function.dependencies)
        assert all(dependency.module == "common" for dependency in dependencies)
    assert all(
        not isinstance(node, ast.ImportFrom)
        or node.module in {"query.database.compile", "query.database.compile.common.functions"}
        for node in tree.body
    )


def test_query_execution_modules_stay_outside_common():
    directory = Path(query_functions.__file__).parent
    assert {path.name for path in directory.glob("*.py")} == {
        "__init__.py", "direct.py", "time_series.py", "cross_section.py",
        "runtime.py", "dispatch.py",
    }
    common_directory = Path(common_functions.__file__).parent
    assert not (common_directory / "runtime.py").exists()
    assert not (common_directory / "dispatch.py").exists()
    for name in ("runtime", "dispatch"):
        module = importlib.import_module("query.database.compile.query.functions." + name)
        definitions = [value for value in vars(module).values() if isinstance(value, DolphinDBFunction)]
        local = [function for function in definitions if function.module == "query"]
        assert local
        assert not {function.name for function in local}.intersection(function.name for function in OPERATOR_FUNCTIONS)
    assert all(function.module == "query" for function in QUERY_FUNCTIONS)


def test_common_exports_helpers_without_query_execution():
    operators = {function.name for function in OPERATOR_FUNCTIONS}
    helpers = collect_functions(COMMON_FUNCTIONS, "common")
    assert len(helpers) == len({function.name for function in helpers})
    assert not operators.intersection(function.name for function in helpers)
    definitions = []
    directory = Path(common_functions.__file__).parent
    for path in directory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module = importlib.import_module("query.database.compile.common.functions." + path.stem)
        for node in tree.body:
            if not (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "DolphinDBFunction"
            ):
                continue
            function = getattr(module, node.targets[0].id)
            assert isinstance(function, DolphinDBFunction)
            assert function.module == "common"
            assert all(dependency.module == "common" for dependency in function.dependencies)
            definitions.append(function)
    assert len(definitions) == len(helpers)
    assert {id(function) for function in definitions} == {id(function) for function in helpers}
    operator_dependencies = collect_functions(
        dependency for operator in OPERATOR_FUNCTIONS for dependency in operator.dependencies
    )
    assert set(operator_dependencies) <= set(helpers)
    query_helpers = {
        function for function in collect_functions(QUERY_FUNCTIONS, "query")
        if function.module == "common"
    }
    assert set(helpers) == query_helpers


def test_query_entry_remains_in_the_query_script():
    module = importlib.import_module("query.database.compile.query.scripts")
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "QUERY_SCRIPT" for target in node.targets)
    )
    assert isinstance(assignment.value, ast.Constant)
    assert "def buildQuery(request)" in assignment.value.value
    assert not hasattr(common_functions, "BUILD_QUERY")


def test_query_compilation_includes_operators_helpers_and_execution_once():
    expected = {function.name for function in collect_functions(QUERY_FUNCTIONS, "query")}
    script = compile()
    names = re.findall(r"^def (\w+)\(", script, re.M)
    assert len(names) == len(set(names))
    assert set(names) == expected | {"buildQuery"}
    assert not re.search(r"^\s*(?:module\s|use\s+(?:common|query)\b)", script, re.M)
