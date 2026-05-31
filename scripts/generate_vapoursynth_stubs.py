from __future__ import annotations

import argparse
import ast
import copy
import keyword
import os
import sys
from pathlib import Path
from typing import Iterator, Sequence

import vapoursynth


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    template = Path(__file__).with_name("vapoursynth.pyi.in").read_text(encoding="utf-8")
    plugins_core, plugins_video, plugins_audio = plugin_stubs(vapoursynth.core.plugins())
    stub = template.replace("# inject Core plugins", plugins_core)
    stub = stub.replace("# inject VideoNode plugins", plugins_video)
    stub = stub.replace("# inject AudioNode plugins", plugins_audio)

    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(stub, encoding="utf-8", newline="\n")
    os.replace(temp, output)
    generate_helper_module_stubs(output.parent)
    return 0


def plugin_stubs(plugins: Iterator[object], indent: int = 4) -> tuple[str, str, str]:
    core_blocks: list[str] = []
    video_blocks: list[str] = []
    audio_blocks: list[str] = []

    for plugin in plugins:
        namespace = plugin.namespace
        name = plugin.name
        core_lines = [f"class {namespace}(Plugin):", f'    """{name}"""']
        video_lines = [f"class {namespace}(Plugin):", f'    """{name}"""']
        audio_lines = [f"class {namespace}(Plugin):", f'    """{name}"""']

        for function in plugin.functions():
            core, video, audio = function_stubs(namespace, function)
            if core is not None:
                core_lines.extend(core)
            if video is not None:
                video_lines.extend(video)
            if audio is not None:
                audio_lines.extend(audio)

        if len(core_lines) > 2:
            core_blocks.extend(core_lines)
        if len(video_lines) > 2:
            video_blocks.extend(video_lines)
        if len(audio_lines) > 2:
            audio_blocks.extend(audio_lines)

    prefix = " " * indent
    return (
        "\n".join(prefix + line for line in core_blocks),
        "\n".join(prefix + line for line in video_blocks),
        "\n".join(prefix + line for line in audio_blocks),
    )


def function_stubs(namespace: str, function: object) -> tuple[list[str] | None, list[str] | None, list[str] | None]:
    signature = signature_vs2py(function.signature)
    return_signature = return_signature_vs2py(function.return_signature, signature, function.name)
    core_definition = [
        "    @staticmethod",
        f"    def {function.name}({','.join(signature)}) -> {return_signature}: ...",
    ]
    node_definition = [
        "    @staticmethod",
        f"    def {function.name}({','.join(signature[1:])}) -> {return_signature}: ...",
    ]

    return (
        core_definition if has_injected_function(vapoursynth.core, namespace, function.name) else None,
        node_definition if has_injected_function(blank_video_node(), namespace, function.name) else None,
        node_definition if has_injected_function(blank_audio_node(), namespace, function.name) else None,
    )


def signature_vs2py(signature: str) -> list[str]:
    args = signature.strip(";").split(";")

    for index, arg in enumerate(args):
        parts = arg.split(":")
        if len(parts) == 1 and parts[0] == "":
            continue
        if len(parts) == 1 and parts[0] == "any":
            args[index] = "**kwargs: Any"
            continue

        name = parts[0]
        if keyword.iskeyword(name):
            name = f"{name}_"

        value_type = parts[1]
        is_array = value_type.endswith("[]")
        value_type = value_type[:-2] if is_array else value_type
        is_optional = len(parts) >= 3 and parts[2] == "opt"

        value_type = value_type.replace("vnode", "VideoNode").replace("vframe", "VideoFrame")
        value_type = value_type.replace("anode", "AudioNode").replace("aframe", "AudioFrame")
        value_type = value_type.replace("func", "Callable[..., Any]")
        value_type = value_type.replace("data", "Union[str, bytes, bytearray]")
        if is_array:
            value_type = f"Union[{value_type},Sequence[{value_type}]]"
        if is_optional:
            value_type = f"{value_type}=..."

        args[index] = f"{name}: {value_type}"

    return args


def return_signature_vs2py(return_signature: str, inputs: Sequence[str], function_name: str) -> str:
    outputs = signature_vs2py(return_signature)

    for index, output in enumerate(outputs):
        outputs[index] = "None" if output == "" else output.split(":")[-1].strip()

    if len(outputs) == 1 and outputs[0] == "None":
        return "None"
    if len(outputs) == 1 and outputs[0] == "Any":
        first_type = inputs[0].split(":")[-1] if inputs else ""
        if "VideoNode" in first_type:
            return "VideoNode"
        if "AudioNode" in first_type:
            return "AudioNode"
        if "Source" in function_name:
            return "VideoNode"
        return "Any"
    if len(outputs) == 1:
        return outputs[0]

    return f"Union[{','.join(outputs)}]"


def has_injected_function(node: object | None, namespace: str, function_name: str) -> bool:
    if node is None:
        return False

    try:
        return hasattr(getattr(node, namespace), function_name)
    except Exception:
        return False


def blank_video_node() -> object | None:
    try:
        return vapoursynth.core.std.BlankClip()
    except Exception:
        return None


def blank_audio_node() -> object | None:
    try:
        return vapoursynth.core.std.BlankAudio()
    except Exception:
        return None


def generate_helper_module_stubs(output_dir: Path) -> None:
    count = 0
    for script_dir in vapoursynth_script_dirs():
        for source in sorted(script_dir.glob("*.py")):
            if source.name == "__init__.py":
                continue

            target = output_dir / f"{source.stem}.pyi"
            target.write_text(helper_module_stub(source), encoding="utf-8", newline="\n")
            count += 1

    (output_dir / ".helper-stubs").write_text(f"4:{count}", encoding="utf-8")


def vapoursynth_script_dirs() -> list[Path]:
    dirs = []
    for entry in sys.path:
        if not entry:
            continue

        path = Path(entry)
        if path.name == "VapourSynthScripts" and path.is_dir():
            dirs.append(path)

    return unique_paths(dirs)


def unique_paths(paths: Sequence[Path]) -> list[Path]:
    unique = []
    seen = set()
    for path in paths:
        real = path.resolve()
        key = str(real).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(real)

    return unique


def helper_module_stub(source: Path) -> str:
    try:
        tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    except Exception:
        return "\n".join(["from typing import Any", "", "def __getattr__(name: str) -> Any: ...", ""])

    used_names = signature_names(tree)
    alias_names = type_alias_names(tree, used_names)
    used_names.add("Any")
    for node in tree.body:
        if assignment_name(node) in alias_names:
            used_names.update(annotation_names(assignment_value(node)))

    imports = import_lines(tree, used_names)
    lines = ["from typing import Any", *imports, ""]
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.extend(stub_function(node))
        elif isinstance(node, ast.ClassDef):
            lines.extend(stub_class(node))
        elif assignment_name(node) in alias_names:
            lines.append(f"{assignment_name(node)} = {ast.unparse(assignment_value(node))}")
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            lines.append(f"{node.target.id}: {ast.unparse(node.annotation)}")
        elif isinstance(node, ast.Assign):
            for name in assigned_names(node):
                lines.append(f"{name}: {inferred_type(node.value)}")

    if len(lines) == 3:
        lines.append("def __getattr__(name: str) -> Any: ...")

    return "\n".join([*lines, ""])


def signature_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        names.update(node_signature_names(node))

    return names


def node_signature_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        names.update(function_signature_names(node))
    elif isinstance(node, ast.ClassDef):
        for base in node.bases:
            names.update(annotation_names(base))
        for keyword_arg in node.keywords:
            names.update(annotation_names(keyword_arg.value))
        for child in node.body:
            names.update(node_signature_names(child))
            if isinstance(child, ast.AnnAssign):
                names.update(annotation_names(child.annotation))

    return names


def function_signature_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for arg in function_args(node):
        names.update(annotation_names(arg.annotation))
    names.update(annotation_names(node.returns))
    for decorator in node.decorator_list:
        if is_overload_decorator(decorator):
            names.update(annotation_names(decorator))

    return names


def function_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg is not None:
        args.append(node.args.vararg)
    if node.args.kwarg is not None:
        args.append(node.args.kwarg)

    return args


def annotation_names(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()

    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and child.id not in builtin_annotation_names()
    }


def builtin_annotation_names() -> set[str]:
    return {
        "Any",
        "None",
        "NotImplemented",
        "bool",
        "bytearray",
        "bytes",
        "complex",
        "dict",
        "float",
        "frozenset",
        "int",
        "list",
        "object",
        "set",
        "str",
        "tuple",
        "type",
    }


def type_alias_names(tree: ast.Module, used_names: set[str]) -> set[str]:
    alias_names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in tree.body:
            name = assignment_name(node)
            if name is None or name not in used_names or name in alias_names:
                continue

            value = assignment_value(node)
            if value is None or not is_type_expression(value):
                continue

            alias_names.add(name)
            used_names.update(annotation_names(value))
            changed = True

    return alias_names


def assignment_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id

    return None


def assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return node.value

    return None


def is_type_expression(node: ast.AST) -> bool:
    if isinstance(node, (ast.BinOp, ast.Name, ast.Attribute, ast.Subscript)):
        return True
    if isinstance(node, ast.Constant):
        return node.value is None
    if isinstance(node, ast.Tuple):
        return all(is_type_expression(element) for element in node.elts)

    return False


def import_lines(tree: ast.Module, used_names: set[str]) -> list[str]:
    lines = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(import_name(alias) in used_names for alias in node.names):
                line = ast.unparse(node)
                if line not in seen:
                    lines.append(line)
                    seen.add(line)
        elif isinstance(node, ast.ImportFrom):
            if any((alias.asname or alias.name) in used_names for alias in node.names):
                line = ast.unparse(node)
                if line not in seen:
                    lines.append(line)
                    seen.add(line)

    return lines


def import_name(alias: ast.alias) -> str:
    return alias.asname or alias.name.split(".", 1)[0]


def stub_function(node: ast.FunctionDef | ast.AsyncFunctionDef, indent: int = 0) -> list[str]:
    function = copy.deepcopy(node)
    function.decorator_list = [
        decorator for decorator in function.decorator_list if is_overload_decorator(decorator)
    ]
    function.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
    function.type_comment = None
    function.args.defaults = [ast.Constant(value=Ellipsis) for _ in function.args.defaults]
    function.args.kw_defaults = [
        None if default is None else ast.Constant(value=Ellipsis)
        for default in function.args.kw_defaults
    ]
    for arg in function_args(function):
        arg.type_comment = None
        if arg.annotation is None:
            arg.annotation = ast.Name(id="Any", ctx=ast.Load())
    if function.returns is None:
        function.returns = ast.Name(id="Any", ctx=ast.Load())

    prefix = " " * indent
    return [prefix + line for line in ast.unparse(function).splitlines()]


def is_overload_decorator(node: ast.AST) -> bool:
    return ast.unparse(node) in {"overload", "typing.overload"}


def stub_class(node: ast.ClassDef, indent: int = 0) -> list[str]:
    prefix = " " * indent
    bases = [ast.unparse(base) for base in node.bases]
    bases.extend(
        f"{keyword_arg.arg}={ast.unparse(keyword_arg.value)}"
        for keyword_arg in node.keywords
        if keyword_arg.arg is not None
    )
    header = f"{prefix}class {node.name}"
    if bases:
        header += f"({', '.join(bases)})"
    header += ":"

    body = []
    is_enum = is_enum_class(node)
    if is_dataclass_class(node) and not has_method(node, "__init__"):
        body.extend(dataclass_init(node, indent + 4))

    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body.extend(stub_function(child, indent + 4))
        elif isinstance(child, ast.ClassDef):
            body.extend(stub_class(child, indent + 4))
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            body.append(f"{' ' * (indent + 4)}{child.target.id}: {ast.unparse(child.annotation)}")
        elif isinstance(child, ast.Assign):
            for name in assigned_names(child):
                if is_enum and isinstance(child.value, ast.Constant):
                    body.append(f"{' ' * (indent + 4)}{name} = {ast.unparse(child.value)}")
                else:
                    body.append(f"{' ' * (indent + 4)}{name}: {inferred_type(child.value)}")

    if not body:
        body.append(f"{' ' * (indent + 4)}...")

    return [header, *body]


def is_enum_class(node: ast.ClassDef) -> bool:
    return any(ast.unparse(base) in {"Enum", "IntEnum", "enum.Enum", "enum.IntEnum"} for base in node.bases)


def is_dataclass_class(node: ast.ClassDef) -> bool:
    return any(decorator_name(decorator) in {"dataclass", "dataclasses.dataclass"} for decorator in node.decorator_list)


def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        node = node.func

    return ast.unparse(node)


def has_method(node: ast.ClassDef, name: str) -> bool:
    return any(isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name for child in node.body)


def dataclass_init(node: ast.ClassDef, indent: int) -> list[str]:
    params = ["self"]
    for child in node.body:
        if not isinstance(child, ast.AnnAssign) or not isinstance(child.target, ast.Name):
            continue
        if child.target.id.startswith("_") or is_class_var(child.annotation) or not field_init_enabled(child.value):
            continue

        param = f"{child.target.id}: {ast.unparse(child.annotation)}"
        if child.value is not None:
            param += "=..."
        params.append(param)

    prefix = " " * indent
    return [
        f"{prefix}def __init__({', '.join(params)}) -> None:",
        f"{prefix}    ...",
    ]


def is_class_var(node: ast.AST) -> bool:
    text = ast.unparse(node)
    return text == "ClassVar" or text.startswith("ClassVar[") or text.startswith("typing.ClassVar[")


def field_init_enabled(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"field", "dataclasses.field"}:
        return True

    for keyword_arg in node.keywords:
        if keyword_arg.arg == "init" and isinstance(keyword_arg.value, ast.Constant):
            return keyword_arg.value.value is not False

    return True


def inferred_type(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "bool"
        if isinstance(node.value, int):
            return "int"
        if isinstance(node.value, float):
            return "float"
        if isinstance(node.value, str):
            return "str"
        if isinstance(node.value, bytes):
            return "bytes"
    if isinstance(node, ast.List):
        return "list[Any]"
    if isinstance(node, ast.Tuple):
        return "tuple[Any, ...]"
    if isinstance(node, ast.Dict):
        return "dict[Any, Any]"
    if isinstance(node, ast.Set):
        return "set[Any]"

    return "Any"


def assigned_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names = []

    for target in targets:
        if isinstance(target, ast.Name) and not target.id.startswith("_"):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            names.extend(
                element.id
                for element in target.elts
                if isinstance(element, ast.Name) and not element.id.startswith("_")
            )

    return names


if __name__ == "__main__":
    raise SystemExit(main())
