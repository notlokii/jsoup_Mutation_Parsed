#!/usr/bin/env python3
"""
mutationApplier.py
──────────────────────────────────────────────────────────────────────────────
Applies PIT mutations to Java source files using javalang AST parsing.

For every mutation in mutations.xml this script:
  1. Resolves the source file path from the fully-qualified class name.
  2. Parses that file into a javalang AST.
  3. Uses AST node types and positions to validate and locate the mutation
     target before editing source.
  4. Applies the correct semantic transformation for the mutator type.
  5. Writes the mutated file to the output directory.

Supported mutators (14 types covering all PIT defaults):
  RemoveConditionalMutator_EQUAL_IF / ELSE / ORDER_IF / ORDER_ELSE
  ConditionalsBoundaryMutator
  MathMutator
  VoidMethodCallMutator
  BooleanFalseReturnValsMutator / BooleanTrueReturnValsMutator
  NullReturnValsMutator / EmptyObjectReturnValsMutator / PrimitiveReturnsMutator
  IncrementsMutator
  SwitchMutator
  NegateMutator

Usage:
    python scripts/mutationApplier.py
    python scripts/mutationApplier.py --mutations Test/jsoup/target/pit-reports/mutations.xml \\
                                      --project  Test/jsoup/ \\
                                      --output   mutants/ \\
                                      --limit    100
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from utils.paths import DEFAULT_MUTATIONS_XML, DEFAULT_PROJECT_ROOT, resolve_mutations_xml, resolve_project_root

try:
    import javalang
    import javalang.tree as jt
except ImportError:
    sys.exit(
        "[ERROR] javalang is not installed.\n"
        "Run:  pip install javalang\n"
        "or:   pip install -r scripts/requirements.txt"
    )

def resolve_source_path(mutated_class: str, source_file: str, project_root: str) -> str | None:
    """
    Derive the on-disk path from the fully-qualified class name.

    Example:
        mutated_class = "org.jsoup.select.QueryParser"
        source_file   = "QueryParser.java"
        →  <project_root>/src/main/java/org/jsoup/select/QueryParser.java
    """
    parts = mutated_class.split(".")
    package_parts = parts[:-1]          # everything before the simple class name
    rel = os.path.join("src", "main", "java", *package_parts, source_file)
    full = os.path.join(project_root, rel)
    if os.path.isfile(full):
        return full

    matches = list(Path(project_root).glob(f"**/{source_file}"))
    return str(matches[0]) if matches else None
def relative_source_path(source_path: str, project_root: Path) -> Path:
    path = Path(source_path)
    try:
        return path.relative_to(project_root)
    except ValueError:
        return Path("src") / "main" / "java" / path.name


# ──────────────────────────────────────────────────────────────────────────────
# AST helpers
# ──────────────────────────────────────────────────────────────────────────────

def parse_java_ast(source: str):
    """
    Parse Java source into a javalang CompilationUnit.
    Returns the tree, or None if parsing fails (e.g. unsupported syntax).
    """
    try:
        return javalang.parse.parse(source)
    except Exception as exc:
        print(f"    [AST WARN] {exc}")
        return None


def nodes_at_line(tree, line: int, *node_types):
    """
    Walk the javalang AST and return every node whose type is in node_types
    and whose .position.line == line.

    This is the key AST operation: instead of trusting a regex on raw text,
    we confirm the *type* of the construct at this line before mutating.
    """
    if tree is None:
        return []
    hits = []
    for _, node in tree:
        if not isinstance(node, tuple(node_types)):
            continue
        pos = getattr(node, "position", None)
        if pos and pos.line == line:
            hits.append(node)
    return hits


def _indent(line: str) -> str:
    """Return the leading whitespace of a line."""
    return line[: len(line) - len(line.lstrip())]


def replace_parenthesized_expression(line: str, replacement: str) -> str:
    """
    Replace the first top-level (...) contents in a control-flow statement.
    This uses Java delimiters rather than regex mutation of the entire line.
    """
    open_idx = line.find("(")
    if open_idx == -1:
        return line

    depth = 0
    for idx in range(open_idx, len(line)):
        char = line[idx]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return f"{line[:open_idx + 1]}{replacement}{line[idx:]}"

    return line


def replace_return_expression(line: str, replacement: str) -> str:
    """
    Replace the expression in a return statement while preserving indentation
    and any trailing line ending.
    """
    line_ending = "\n" if line.endswith("\n") else ""
    body = line[:-1] if line_ending else line
    stripped = body.strip()
    if not stripped.startswith("return"):
        return line

    semi_idx = body.rfind(";")
    return_idx = body.find("return")
    if semi_idx == -1 or return_idx == -1:
        return line

    prefix = body[: return_idx + len("return")]
    suffix = body[semi_idx:]
    return f"{prefix} {replacement}{suffix}{line_ending}"


# ──────────────────────────────────────────────────────────────────────────────
# Mutator implementations
# Each function receives the original line string, 1-indexed line number,
# the AST tree, and optional extra args.  Returns the mutated line string.
# ──────────────────────────────────────────────────────────────────────────────

def mut_remove_conditional_if(line: str, line_no: int, tree) -> str:
    """
    RemoveConditionalMutator_EQUAL_IF / ORDER_IF
    Replace the boolean condition of an if/while/for with `true`
    so the if-branch is always taken.

    AST guard: confirms an IfStatement, WhileStatement, or ForStatement
    exists at this line before touching anything.
    """
    cf = nodes_at_line(tree, line_no,
                       jt.IfStatement, jt.WhileStatement,
                       jt.DoStatement, jt.ForStatement)
    if cf:
        return replace_parenthesized_expression(line, "true")
    return line


def mut_remove_conditional_else(line: str, line_no: int, tree) -> str:
    """
    RemoveConditionalMutator_EQUAL_ELSE / ORDER_ELSE
    Replace the condition with `false` so the else-branch is always taken.
    """
    cf = nodes_at_line(tree, line_no,
                       jt.IfStatement, jt.WhileStatement,
                       jt.DoStatement, jt.ForStatement)
    if cf:
        return replace_parenthesized_expression(line, "false")
    return line


def mut_conditionals_boundary(line: str, line_no: int, tree) -> str:
    """
    ConditionalsBoundaryMutator
    Shift boundary operators:  < → <=,  <= → <,  > → >=,  >= → >

    AST guard: confirms a BinaryOperation exists at this line, which tells
    us there really is a comparison operator here (not just a generic '<'
    that might be inside a generic type parameter).
    """
    bin_ops = nodes_at_line(tree, line_no, jt.BinaryOperation)
    if not bin_ops:
        return line

    # Use placeholder tokens to avoid double-replacement (e.g. < → <= → <)
    REPLACEMENTS = [
        ("<=", "\x00LE\x00"),
        (">=", "\x00GE\x00"),
        ("<",  "\x00LT\x00"),
        (">",  "\x00GT\x00"),
    ]
    REVERSE = {
        "\x00LE\x00": "<",
        "\x00GE\x00": ">",
        "\x00LT\x00": "<=",
        "\x00GT\x00": ">=",
    }

    result = line
    applied = False
    for old, placeholder in REPLACEMENTS:
        if not applied and old in result:
            result = result.replace(old, placeholder, 1)
            applied = True

    for ph, new in REVERSE.items():
        result = result.replace(ph, new)

    return result


def mut_math(line: str, line_no: int, tree, description: str) -> str:
    """
    MathMutator
    Replace one arithmetic operator with its PIT-defined counterpart.
      + ↔ -,   * ↔ /,   % → 1

    AST guard: confirms a BinaryOperation exists here.
    Description hint is used first, then AST operator attribute as fallback.
    """
    bin_ops = nodes_at_line(tree, line_no, jt.BinaryOperation)
    if not bin_ops:
        return line

    desc = description.lower()

    # Description-driven replacements (more reliable than guessing from text)
    desc_patterns = [
        ("addition",       r'(?<![+\+])\+(?![+=])',    '-'),
        ("subtraction",    r'(?<![-\-])-(?![-=])',     '+'),
        ("multiplication", r'\*(?!=)',                  '/'),
        ("division",       r'/(?!=)',                   '*'),
        ("modulus",        r'%(?!=)',                   '1'),
        ("with -",         r'(?<![+\+])\+(?![+=])',    '-'),
        ("with +",         r'(?<![-\-])-(?![-=])',     '+'),
        ("with /",         r'\*(?!=)',                  '/'),
        ("with *",         r'/(?!=)',                   '*'),
    ]
    for keyword, pattern, replacement in desc_patterns:
        if keyword in desc:
            mutated = re.sub(pattern, replacement, line, count=1)
            if mutated != line:
                return mutated

    # AST-operator fallback
    op_map = {"+": "-", "-": "+", "*": "/", "/": "*", "%": "1"}
    for node in bin_ops:
        op = getattr(node, "operator", None)
        if op and op in op_map:
            mutated = line.replace(f" {op} ", f" {op_map[op]} ", 1)
            if mutated != line:
                return mutated

    return line


def mut_void_method_call(line: str, line_no: int, tree) -> str:
    """
    VoidMethodCallMutator
    Remove a void method call statement entirely.

    AST guard: confirms a MethodInvocation exists at this line.
    The line is replaced with a blank comment preserving line count
    (important if other mutants reference nearby line numbers).
    """
    invocations = nodes_at_line(tree, line_no, jt.MethodInvocation)
    if invocations:
        return _indent(line) + "/* VoidMethodCallMutator: call removed */\n"
    return line


def mut_return_value(line: str, line_no: int, tree,
                     mutator: str, description: str) -> str:
    """
    Return-value mutators:
      BooleanFalseReturnValsMutator  → return false;
      BooleanTrueReturnValsMutator   → return true;
      NullReturnValsMutator          → return null;
      PrimitiveReturnsMutator        → return 0;
      EmptyObjectReturnValsMutator   → return "";  (type inferred from description)

    AST guard: confirms a ReturnStatement exists at this line.
    """
    ret_nodes = nodes_at_line(tree, line_no, jt.ReturnStatement)
    if not ret_nodes:
        return line

    ind = _indent(line)

    if "BooleanFalseReturnValsMutator" in mutator:
        return replace_return_expression(line, "false")

    if "BooleanTrueReturnValsMutator" in mutator:
        return replace_return_expression(line, "true")

    if "NullReturnValsMutator" in mutator:
        return replace_return_expression(line, "null")

    if "PrimitiveReturnsMutator" in mutator:
        return replace_return_expression(line, "0")

    if "EmptyObjectReturnValsMutator" in mutator:
        desc = description.lower()
        if '""' in description or "empty string" in desc or "string" in desc:
            return replace_return_expression(line, '""')
        if "list" in desc or "emptylist" in desc:
            return replace_return_expression(line, "java.util.Collections.emptyList()")
        if "set" in desc or "emptyset" in desc:
            return replace_return_expression(line, "java.util.Collections.emptySet()")
        if "optional" in desc:
            return replace_return_expression(line, "java.util.Optional.empty()")
        if "map" in desc:
            return replace_return_expression(line, "java.util.Collections.emptyMap()")
        return replace_return_expression(line, '""')

    return line


def mut_increments(line: str, line_no: int, tree) -> str:
    """
    IncrementsMutator
    ++ → --,  -- → ++,  += → -=,  -= → +=

    AST guard: confirms a MemberReference or Assignment at this line.
    """
    hits = nodes_at_line(tree, line_no,
                         jt.MemberReference, jt.Assignment,
                         jt.StatementExpression)
    if not hits:
        return line

    for old, new in [("++", "--"), ("--", "++"), ("+=", "-="), ("-=", "+=")]:
        if old in line:
            return line.replace(old, new, 1)
    return line


def mut_switch(line: str, line_no: int, tree) -> str:
    """
    SwitchMutator
    PIT removes a case by making its label unreachable.
    We shift integer case values by +1000 so they never match.

    AST guard: confirms a SwitchStatementCase at this line.
    """
    switch_cases = nodes_at_line(tree, line_no, jt.SwitchStatementCase)

    match = re.match(r'^(\s*case\s+)(\d+)(\s*:.*)', line)
    if match and switch_cases:
        prefix, val, suffix = match.groups()
        return f"{prefix}{int(val) + 1000}{suffix}\n"
    return line


def mut_negate(line: str, line_no: int, tree) -> str:
    """
    NegateConditionalsMutator / INVERT_NEGS
    Negate unary minus:  -x → x,  x → -x
    Negate boolean:  true → false,  false → true  (for simple literal lines)
    """
    bin_ops = nodes_at_line(tree, line_no, jt.BinaryOperation,
                            jt.MethodInvocation, jt.MemberReference)
    if not bin_ops:
        return line

    # Unary negation flip
    if re.search(r'(?<![=!<>])-(?![-=>])', line):
        return re.sub(r'(?<![=!<>])-(?![-=>])', '', line, count=1)

    return line


# ──────────────────────────────────────────────────────────────────────────────
# Dispatch table
# ──────────────────────────────────────────────────────────────────────────────

def apply_single_mutation(source_lines: list, line_idx: int,
                          mutator: str, description: str, tree) -> str:
    """
    Route to the correct mutator function.
    Returns the (possibly mutated) line string.
    line_idx is 0-indexed; line_no passed to helpers is 1-indexed.
    """
    line    = source_lines[line_idx]
    line_no = line_idx + 1

    # ── Conditional removal ───────────────────────────────────────────────────
    if ("RemoveConditionalMutator_EQUAL_IF"   in mutator or
            "RemoveConditionalMutator_ORDER_IF"   in mutator):
        return mut_remove_conditional_if(line, line_no, tree)

    if ("RemoveConditionalMutator_EQUAL_ELSE" in mutator or
            "RemoveConditionalMutator_ORDER_ELSE" in mutator):
        return mut_remove_conditional_else(line, line_no, tree)

    # ── Boundary ──────────────────────────────────────────────────────────────
    if "ConditionalsBoundaryMutator" in mutator:
        return mut_conditionals_boundary(line, line_no, tree)

    # ── Math ──────────────────────────────────────────────────────────────────
    if "MathMutator" in mutator:
        return mut_math(line, line_no, tree, description)

    # ── Void call removal ─────────────────────────────────────────────────────
    if "VoidMethodCallMutator" in mutator:
        return mut_void_method_call(line, line_no, tree)

    # ── Return value mutators ─────────────────────────────────────────────────
    RETURN_MUTATORS = (
        "BooleanFalseReturnValsMutator",
        "BooleanTrueReturnValsMutator",
        "NullReturnValsMutator",
        "EmptyObjectReturnValsMutator",
        "PrimitiveReturnsMutator",
    )
    if any(x in mutator for x in RETURN_MUTATORS):
        return mut_return_value(line, line_no, tree, mutator, description)

    # ── Increments ────────────────────────────────────────────────────────────
    if "IncrementsMutator" in mutator:
        return mut_increments(line, line_no, tree)

    # ── Switch ────────────────────────────────────────────────────────────────
    if "SwitchMutator" in mutator:
        return mut_switch(line, line_no, tree)

    # ── Negate ────────────────────────────────────────────────────────────────
    if "NegateConditionalsMutator" in mutator or "INVERT_NEGS" in mutator:
        return mut_negate(line, line_no, tree)

    # Unhandled
    print(f"    [SKIP] No handler for: {mutator.split('.')[-1]}")
    return line


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mutations", default=str(DEFAULT_MUTATIONS_XML),
                        help="Path to PIT mutations.xml or project root  (default: Test/jsoup/target/pit-reports/mutations.xml)")
    parser.add_argument("--project",   default=str(DEFAULT_PROJECT_ROOT),
                        help="Root of the Maven project  (default: Test/jsoup/)")
    parser.add_argument("--output",    default="mutants",
                        help="Output directory for mutated files  (default: mutants/)")
    parser.add_argument("--limit",     type=int, default=None,
                        help="Cap on mutations to process (useful for quick tests)")
    args = parser.parse_args()

    mutations_xml = resolve_mutations_xml(args.mutations)
    project_root = resolve_project_root(args.project, mutations_xml)
    output_root = Path(args.output).expanduser()
    output_root.mkdir(parents=True, exist_ok=True)

    # ── Load mutation report ──────────────────────────────────────────────────
    xml_tree = ET.parse(str(mutations_xml))
    all_mutations = xml_tree.getroot().findall("mutation")
    total = len(all_mutations)
    limit = args.limit or total
    print(f"Loaded {total} mutations from {mutations_xml}.  Processing up to {limit}.\n")

    stats = defaultdict(int)
    ast_cache: dict = {}   # source_path → (lines, tree)  — parsed once per file

    for i, mut in enumerate(all_mutations[:limit]):

        # ── Extract fields ────────────────────────────────────────────────────
        def txt(tag):
            el = mut.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        source_file    = txt("sourceFile")
        mutated_class  = txt("mutatedClass")
        line_number    = int(txt("lineNumber"))
        mutator        = txt("mutator")
        description    = txt("description")

        # ── Resolve source path using full class name (not just filename) ─────
        src_path = resolve_source_path(mutated_class, source_file, str(project_root))
        if src_path is None:
            stats["skipped_path_not_found"] += 1
            continue

        # ── Load & cache AST (expensive: parse each file only once) ──────────
        if src_path not in ast_cache:
            with open(src_path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            src_lines = raw.splitlines(keepends=True)
            ast_tree  = parse_java_ast(raw)
            ast_cache[src_path] = (src_lines, ast_tree)

        src_lines, ast_tree = ast_cache[src_path]

        if line_number < 1 or line_number > len(src_lines):
            stats["skipped_line_out_of_range"] += 1
            continue

        # ── Apply mutation ────────────────────────────────────────────────────
        try:
            mutated_line = apply_single_mutation(
                src_lines, line_number - 1, mutator, description, ast_tree
            )
        except Exception as exc:
            print(f"  [ERROR] mutation {i}: {exc}")
            stats["failed"] += 1
            continue

        original_line = src_lines[line_number - 1]
        if mutated_line == original_line:
            stats["no_change"] += 1
            continue

        # ── Write mutated file ────────────────────────────────────────────────
        new_lines = src_lines.copy()
        new_lines[line_number - 1] = mutated_line

        rel_src_path = relative_source_path(src_path, project_root)
        mutant_dir = output_root / f"mutant_{i:05d}"
        out_path = mutant_dir / rel_src_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        simple_class = mutated_class.split(".")[-1]
        short_mutator = mutator.split(".")[-1][:42]
        print(f"  [{i:5d}]  {simple_class:<30}  line {line_number:4d}  {short_mutator}")
        stats["created"] += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * 56}")
    print(f"  Mutant files created       : {stats['created']}")
    print(f"  Skipped (file not found)   : {stats['skipped_path_not_found']}")
    print(f"  Skipped (no AST change)    : {stats['no_change']}")
    print(f"  Skipped (line out of range): {stats['skipped_line_out_of_range']}")
    print(f"  Errors                     : {stats['failed']}")
    print(f"  Total processed            : {min(limit, total)}")
    print(f"{'─' * 56}")

    # Write manifest for traceability
    manifest = {
        "stats":    dict(stats),
        "total":    total,
        "processed": min(limit, total),
        "mutations_xml": str(mutations_xml),
        "project":  str(project_root),
        "output":   str(output_root),
    }
    manifest_path = output_root / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest → {manifest_path}")


if __name__ == "__main__":
    main()
