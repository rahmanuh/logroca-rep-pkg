# LogRoca Replication Package

This package accompanies the manuscript *“Supporting Railway Test Failure Analysis with Local Large Language Models: Lessons Learned from Industry”* It contains selected experiment scripts, survey materials, references, and supporting log artefacts.

## Data availability

Test execution logs, test cases, and requirements may contain confidential information and are therefore not included in full. These materials are available from the authors upon request, subject to applicable access restrictions.

The survey generator uses dummy experiment data and supporting files in place of the restricted artefacts. Replace these placeholders with the corresponding approved data before generating surveys for an actual study. See the [survey-page README](survey-page/README.md) for instructions.

## Package contents

| Directory | Contents |
| --- | --- |
| [`literatures/`](literatures/) | Reference bibliography files (`references.bib` and `references.pdf`). |
| [`scripts/`](scripts/) | Experiment and utility scripts. See the [scripts README](scripts/README.md) for usage notes and prerequisites. |
| [`survey-page/`](survey-page/) | Survey-page generator, example data, and supporting files. |

## Reproducing the experiments

The experiment scripts require LogRoca v0.5.0 and access to the relevant dataset. See [`scripts/README.md`](scripts/README.md) for setup details. The survey generator can be run with the included dummy data; using study data requires authorised access to the corresponding experiment results and HTML logs.
