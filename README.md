# jsoup PIT Mutation Testing

This repository packages a Jsoup mutation-testing artifact in the layout requested for the assignment:

- `Test/` contains the Java project under test
- `scripts/` contains the Python and shell automation
- this `README.md` explains how to run everything end to end

## Project Choice

This submission uses **jsoup** from the artifact bundle instead of `lang3`.

## Requirements

- macOS or Linux
- Java 8 available locally
- Maven available on `PATH`
- Python 3

## Repository Layout

```text
.
├── Test/
│   ├── pom.xml
│   ├── src/
│   └── evosuite_tests/
├── scripts/
│   ├── run_pit.sh
│   ├── run_pipeline.sh
│   ├── parse_mutations.py
│   ├── apply_mutations.py
│   └── requirements.txt
└── README.md
```

## Install Python Dependency

```bash
python3 -m pip install -r scripts/requirements.txt
```

## Run PIT Only

From the repository root:

```bash
./scripts/run_pit.sh
```

What this does:

1. selects Java 8
2. builds the `Test/` project
3. runs PIT with the XML settings required by the assignment
4. copies the generated PIT files to `Test/target/pit-reports/`

Expected outputs:

- `Test/target/pit-reports/mutations.xml`
- `Test/target/pit-reports/linecoverage.xml`

## Run The Full Pipeline

From the repository root:

```bash
./scripts/run_pipeline.sh
```

This runs:

1. PIT mutation testing
2. XML parsing into CSV and JSON
3. mutant recreation into source trees

Expected outputs:

- `Test/target/pit-reports/mutations.xml`
- `reports/mutations.csv`
- `reports/summary.json`
- `mutants/manifest.json`
- `mutants/mutant_XXXXX/src/main/java/...`

## Manual Commands

If you want to run each step yourself:

```bash
./scripts/run_pit.sh
python3 scripts/parse_mutations.py --mutations Test/target/pit-reports/mutations.xml --output reports
python3 scripts/apply_mutations.py --mutations Test/target/pit-reports/mutations.xml --project Test --output mutants
```

## Notes On The Mutant Recreator

The mutation recreation script uses `javalang` to parse Java and identify AST nodes before applying a mutation. Because `javalang` does not provide a source-code pretty printer, the final file emission uses AST-guided source edits rather than blind whole-file search-and-replace.

## Important Runtime Note

The PIT run on this artifact is **long-running**. A full run can take a substantial amount of time depending on machine speed. The command should be treated as a batch job rather than a short feedback loop.

