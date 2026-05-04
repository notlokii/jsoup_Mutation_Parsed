# jsoup Mutation Parsing Toolkit

This repository is organized as a compact assignment repo, closer in spirit to [c2nes/javalang](https://github.com/c2nes/javalang): one obvious project directory, one scripts directory, and a single top-level README.

## Layout

```text
.
├── README.md
├── deliverables/
│   ├── jsoup_final_report.docx
│   └── jsoup_final_report.md
├── Test/
│   └── jsoup/
│       ├── pom.xml
│       ├── src/
│       ├── evosuite_tests/
│       └── tests_without_assertion/
└── scripts/
    ├── mutationApplier.py
    ├── parsePitXml.py
    ├── requirements.txt
    ├── run_pipeline.sh
    ├── run_pit.sh
    └── utils/
```

## What Is Different From `javalang`

This repo is similar in structure, but not identical in purpose. `javalang` is a Python library repo with its package at the root, while this is an assignment repo centered on a Java project plus PIT-processing scripts. The similarity is in the simplified layout and root-level clarity, not the language stack.

## Requirements

- Java 8
- Maven
- Python 3

## Install

```bash
python3 -m pip install -r scripts/requirements.txt
```

## Run PIT

```bash
./scripts/run_pit.sh
```

This builds `Test/jsoup/` and writes the PIT XML report to `Test/jsoup/target/pit-reports/mutations.xml`.

## Run The Full Pipeline

```bash
./scripts/run_pipeline.sh
```

This will:

1. run PIT on the jsoup project
2. parse the PIT XML into `reports/`
3. recreate mutated source files in `mutants/`

## Run Individual Steps

```bash
python3 scripts/parsePitXml.py --mutations Test/jsoup/target/pit-reports/mutations.xml --output reports
python3 scripts/mutationApplier.py --mutations Test/jsoup/target/pit-reports/mutations.xml --project Test/jsoup --output mutants
```

## Deliverables

The final written submission files are included in `deliverables/`:

- `deliverables/jsoup_final_report.docx`
- `deliverables/jsoup_final_report.md`

## Notes

The mutation application step uses `javalang` for AST-aware edits instead of blind string replacement. Generated directories such as `reports/`, `mutants/`, and build output are intentionally ignored so the pushed repository stays clean.
