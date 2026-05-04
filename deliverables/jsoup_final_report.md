# PIT Mutation Testing Final Report

**Repository Link:** [https://github.com/notlokii/jsoup_Mutation_Parsed](https://github.com/notlokii/jsoup_Mutation_Parsed)

## OVERVIEW

This project focused on mutation testing with PIT for a Java-based project and on building supporting scripts to parse mutation reports and recreate mutated source files. The assigned project used **jsoup** as the Java codebase under test. In addition to configuring PIT in `pom.xml`, the work also included developing Python tooling to process `mutations.xml` and generate mutated source outputs.

The overall goal was to understand how mutation testing measures test effectiveness, how PIT integrates into a Maven-based Java project, and how tool-building can automate analysis beyond the default PIT reports.

## PROJECT SETUP

The jsoup project was organized under `Test/jsoup/`, with a `scripts/` directory containing the automation utilities:

- `parsePitXml.py`
- `mutationApplier.py`
- `run_pit.sh`
- `run_pipeline.sh`

The repository was also restructured so that it clearly separates the Java project, scripts, and documentation. Before running PIT, the project was built and tested using Maven:

```bash
mvn test
```

This confirmed that the project test suite was working correctly before mutation analysis. The final successful test run reported:

- Tests run: `7967`
- Failures: `0`
- Errors: `0`
- Build result: `BUILD SUCCESS`

## RUNNING PIT MUTATION TESTING

PIT was configured inside `Test/jsoup/pom.xml` with XML output and line coverage export enabled. The plugin configuration includes:

- selected mutators such as `MATH`, `INCREMENTS`, `NULL_RETURNS`, and `REMOVE_CONDITIONALS`
- `fullMutationMatrix=true`
- `exportLineCoverage=true`
- `outputFormats=XML`

The general PIT command used for this project is:

```bash
mvn test-compile org.pitest:pitest-maven:mutationCoverage
```

During testing, a full-project PIT execution produced worker `RUN_ERROR` instability with some EvoSuite-generated tests. To complete a stable end-to-end demonstration of the pipeline, a targeted PIT execution was used on `org.jsoup.parser.ParseError`:

```bash
mvn clean test-compile org.pitest:pitest-maven:mutationCoverage \
  -DtargetClasses=org.jsoup.parser.ParseError \
  -DtargetTests='org.jsoup.parser.ParseError_ESTest*' \
  -Dthreads=1
```

This targeted run successfully generated valid PIT output files and terminal statistics.

## PIT RESULTS

The successful targeted PIT run produced the following final statistics:

- Line Coverage: `7/24 (29%)`
- Generated mutations: `4`
- Killed mutations: `0`
- Mutations with no coverage: `2`
- Test strength: `0%`
- Tests executed: `8`

Although the mutation score for this targeted run was low, it still provided valid mutation artifacts and demonstrated that the PIT configuration, XML export, and downstream tooling all worked end to end.

## MUTATION REPORTS

After execution, PIT generated reports in:

```text
Test/jsoup/target/pit-reports/
```

The key files were:

- `mutations.xml`
- `linecoverage.xml`

The `mutations.xml` file stores structured mutation entries, including:

- source file
- mutated class
- mutated method
- line number
- mutator type
- mutation status

These XML reports were then used as input for the custom Python tooling.

## APPLYING MUTATIONS TO SOURCE CODE

The Python script `scripts/mutationApplier.py` was implemented to recreate mutations directly in the Java source files. The script does not rely on blind string replacement alone. Instead, it uses **javalang** to parse Java source into an AST and then checks node types and positions before applying a mutation.

The script performs the following steps:

1. Reads mutation entries from `mutations.xml`
2. Locates the matching Java source file in `Test/jsoup/src/main/java/`
3. Parses the file with `javalang`
4. Applies a mutation-specific source transformation
5. Writes the mutated file into a separate `mutants/` directory

The command used was:

```bash
python3 scripts/mutationApplier.py \
  --mutations Test/jsoup/target/pit-reports/mutations.xml \
  --project Test/jsoup \
  --output mutants
```

The final execution summary showed:

- Mutant files created: `4`
- Skipped (file not found): `0`
- Skipped (no AST change): `0`
- Skipped (line out of range): `0`
- Errors: `0`
- Total processed: `4`

This confirms that the script successfully processed and recreated all mutations in the selected PIT report.

## PROGRESS

The following project work was completed:

- reorganized the repository into a cleaner structure with `Test/jsoup`, `scripts`, and `README.md`
- configured PIT in `pom.xml` with XML and line coverage export
- verified that `mvn test` passes successfully
- executed PIT and generated mutation reports
- implemented Python tooling for mutation parsing and mutation application
- validated the mutation application flow with generated mutant outputs
- pushed all deliverables to GitHub with documentation

## WHAT I LEARNED

This project helped me better understand mutation testing as a way to measure test quality rather than just code coverage. I learned how PIT creates mutants, how those mutants are evaluated against a test suite, and how mutation statistics can reveal weaknesses that normal unit-test pass/fail results do not show.

I also learned more about practical Java build tooling with Maven, especially how plugin configuration in `pom.xml` affects testing workflows. On the scripting side, I learned how to build supporting developer tools in Python and how AST-based processing is more reliable than plain text replacement when modifying source code.

## HOW THIS PROJECT WAS BENEFICIAL

This project was beneficial because it connected several practical software engineering skills in one workflow:

- Java project setup and build verification
- Maven and plugin configuration
- mutation testing with PIT
- debugging tool/runtime issues
- Python script development for automation
- AST-aware source transformation
- repository organization and documentation

Working through these steps made the assignment feel like a realistic engineering task rather than an isolated coding exercise. It required debugging, tool integration, scripting, and documentation, which are all useful in real development environments.

## DELIVERABLES

All deliverables are available in the GitHub repository:

- Repository: [https://github.com/notlokii/jsoup_Mutation_Parsed](https://github.com/notlokii/jsoup_Mutation_Parsed)
- Java project under test: `Test/jsoup/`
- PIT configuration: `Test/jsoup/pom.xml`
- Mutation parsing script: `scripts/parsePitXml.py`
- Mutation recreation script: `scripts/mutationApplier.py`
- Pipeline scripts: `scripts/run_pit.sh`, `scripts/run_pipeline.sh`
- Generated mutant outputs: `mutants/`
- Documentation: `README.md`

## CONCLUSION

This project demonstrated how mutation testing can be used to evaluate the strength of a test suite and how additional tooling can make mutation reports more actionable. PIT provided mutation and coverage data, while the Python scripts extended that workflow by parsing XML reports and recreating mutated source files for inspection.

Overall, the project reinforced the importance of testing quality, automation, and tool-building in software engineering. It also showed that even when a full mutation run is unstable, a carefully scoped and documented workflow can still validate the tooling pipeline and produce meaningful results.
