# LogRoca Output Assessment Survey

This directory contains the tools and supporting files used to generate individual HTML surveys for evaluating LogRoca outputs. The generator creates one survey for each assigned rater and packages each survey with the corresponding HTML log files.

## Contents

- `generate_surveys.py` — generates the rater-specific survey pages and ZIP packages.
- `survey_data_dummy.csv` — example input data currently used by the generator.
- `html_logs/` — HTML versions of the test logs referenced by the input data.
- `survey_page.example.html` — an example of a generated survey page.
- `survey_questions.md` — the questions and rating criteria used in the survey.
- `INFO.md` — participant instructions embedded in the generated survey pages.
- `requirements.txt` — Python package requirements.

## Requirements

Python and the packages listed in `requirements.txt` are required. From this directory, install them with:

```bash
python -m pip install -r requirements.txt
```

## Prepare the input data

By default, `generate_surveys.py` reads `survey_data_dummy.csv`. Before generating surveys for a study, replace this example data with the approved experiment results, or update the `data_file` path in `main()` to point to the desired CSV.

The CSV must include these columns:

| Column | Purpose |
| --- | --- |
| `experiment_id` | Identifies the LogRoca output being evaluated. |
| `log_file_name` | Names the source log file, such as `log_0000.json`. |
| `root_cause_output` | LogRoca's root-cause prediction. |
| `root_cause_origin_output` | LogRoca's root-cause-origin prediction. |
| `action_suggestions_output` | LogRoca's suggested actions. |
| `rationale_output` | LogRoca's rationale. |
| `truncated_log_content` | Log excerpt shown in the survey. |
| `truncated_kb_context` | Retrieved test-case and requirements context shown in the survey. |

For each referenced JSON log, provide the corresponding HTML log in `html_logs/` (for example, `log_0000.html` for `log_0000.json`). The generator reports a warning when a referenced HTML log is missing.

## Generate the surveys

Run the generator from this directory:

```bash
python generate_surveys.py
```

The script assigns six samples to each of 11 raters and creates the following files in this directory:

- `survey_rater_1.html` through `survey_rater_11.html`
- `survey_rater_1.zip` through `survey_rater_11.zip`

Each ZIP package contains the rater's HTML survey and the HTML logs referenced by that survey, stored in a `logs/` folder inside the package.

## Completing a survey

Raters review each LogRoca output and its supporting log and knowledge-base excerpts, then answer the four output-rating questions on a five-point Likert scale. The page supports saving and restoring progress. When finished, raters download their responses as a CSV file using the page's **Save Final Responses as CSV** button.
