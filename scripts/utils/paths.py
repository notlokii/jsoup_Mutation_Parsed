from pathlib import Path


DEFAULT_PROJECT_ROOT = Path("Test") / "jsoup"
DEFAULT_MUTATIONS_XML = DEFAULT_PROJECT_ROOT / "target" / "pit-reports" / "mutations.xml"


def resolve_mutations_xml(path_hint: str) -> Path:
    """
    Resolve the PIT report path.
    Accept either an explicit file path, a project root, or fall back to a
    few common report locations used by this jsoup setup.
    """
    candidate = Path(path_hint).expanduser()
    if candidate.is_file():
        return candidate

    search_roots = []
    if candidate.exists() and candidate.is_dir():
        search_roots.append(candidate)

    search_roots.extend([
        Path.cwd(),
        Path.cwd() / DEFAULT_PROJECT_ROOT,
        Path.cwd() / DEFAULT_PROJECT_ROOT / "target" / "pit-reports",
    ])

    common_names = [
        "target/pit-reports/mutations.xml",
        "pit-reports/mutations.xml",
        str(DEFAULT_MUTATIONS_XML),
    ]

    for root in search_roots:
        for name in common_names:
            xml_path = root / name
            if xml_path.is_file():
                return xml_path

        matches = sorted(
            root.glob("**/target/pit-reports/mutations.xml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]

    raise FileNotFoundError(
        f"Could not locate mutations.xml from '{path_hint}'. "
        "Expected Test/jsoup/target/pit-reports/mutations.xml or an explicit file path."
    )


def resolve_project_root(path_hint: str, mutations_xml: Path) -> Path:
    """
    Accept either a direct project root or infer it from the mutations.xml path.
    """
    candidate = Path(path_hint).expanduser()
    if candidate.is_dir() and (candidate / "src" / "main" / "java").exists():
        return candidate

    if candidate.is_dir() and (candidate / DEFAULT_PROJECT_ROOT / "src" / "main" / "java").exists():
        return candidate / DEFAULT_PROJECT_ROOT

    for base in [
        mutations_xml.parent.parent,
        mutations_xml.parent.parent.parent,
        Path.cwd() / DEFAULT_PROJECT_ROOT,
    ]:
        if base.exists() and (base / "src" / "main" / "java").exists():
            return base

    raise FileNotFoundError(
        f"Could not resolve Maven project root from '{path_hint}'. "
        "Expected a directory containing src/main/java."
    )
