#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/Test"

if [[ "$(uname -s)" == "Darwin" && -z "${JAVA_HOME:-}" ]]; then
  JAVA_HOME="$(/usr/libexec/java_home -v 1.8)"
fi

if [[ -z "${JAVA_HOME:-}" ]]; then
  echo "JAVA_HOME is not set. Point it to a Java 8 JDK before running this script." >&2
  exit 1
fi

export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

cd "$PROJECT_DIR"

echo "Using JAVA_HOME=$JAVA_HOME"
echo "Building project with Java 8..."
mvn clean test -PtestID -Dtest.dir=src -PtargetID -Dtarget.dir=target

echo "Running PIT mutation coverage..."
mvn org.pitest:pitest-maven:mutationCoverage -PtestID -Dtest.dir=src -PtargetID -Dtarget.dir=target

if [[ ! -s "$PROJECT_DIR/target/pit-reports/mutations.xml" ]]; then
  echo "PIT finished without creating Test/target/pit-reports/mutations.xml" >&2
  exit 1
fi

echo "PIT report ready at:"
echo "  $PROJECT_DIR/target/pit-reports/mutations.xml"

