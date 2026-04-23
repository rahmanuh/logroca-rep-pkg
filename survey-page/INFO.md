# LogRoca Output Assessment Survey

Welcome to the LogRoca Output Assessment Survey.

LogRoca (Log Root Cause Analyst) is an LLM-powered tool designed to assist engineers in performing root cause analysis of test failures. It analyzes test log files and retrieves related test cases and requirements to provide broader context.

In this survey, your task is to evaluate the output of the LogRoca and rate the output given the corresponding test case, requirement, and log excerpt. The log excerpt, test case, and requirements in this experiments are from TCMS test execution of SJ250 project.

## Your Tasks

1. **Watch** the LogRoca video demo.
2. **Download** one of the .zip package.
3. **Answer** demographic questions.
4. **Review LogRoca's output** (root cause, root cause origin, action suggestions, and rationale) along with the corresponding excerpts from the test log, test case, and requirements. Some excerpts may be intentionally truncated due to the LLM’s context window limitations.
5. **Rate each statement** of the output.  
   The page includes an autosave mechanism, along with `Save Progress` and `Load Progress` buttons for manual saving and loading.
6. (Optional) **Add comments** about the LogRoca output.
7. **Answer** 3 conclusion questions.
8. When you have finished all questions, **Save your final responses** by clicking `Save Final Responses as CSV`.
9. **Send the CSV file to rahmanu.hermawan@mdu.se**.

## Rating Instructions

For each LogRoca output, rate your level of agreement (1-5 scale):

**1 = Strongly Disagree | 2 = Disagree | 3 = Neutral | 4 = Agree | 5 = Strongly Agree**

1. **Root cause:** "The root cause prediction is correct."
2. **Root cause origin:** "The root cause origin prediction points to the correct source document."
3. **Action suggestions:** "The action suggestions are useful and relevant to the root cause and root cause origin."
4. **Rationale:** "The rationale is understandable, clear, and related to the root cause, root cause origin, and action suggestions."

## Content Included

- LogRoca output.
- Excerpts from the test log; which is the actual excerpts that are incorporated in the prompt to the LLM.
- Excerpts from the test case; which is the actual excerpts that are incorporated in the prompt to the LLM.
- Excerpts from the requirements; which is the actual excerpts that are incorporated in the prompt to the LLM.
- The full test log file in HTML format.

## LogRoca Output Components

- **Root cause:** LogRoca predicts the root cause as one of:
    - `misconfiguration`: Issues with system configuration or setup.
    - `signal_timeout`: Timeouts while waiting for expected signals or responses.
    - `expired_bugfix`: Expired bugfix that has reappeared or weren't properly fixed.
    - `test_aborted`: The test execution was terminated or interrupted.
    - `unknown`: The root cause cannot be determined from the available information.

- **Root cause origin:** LogRoca predicts where the root cause originates:
    - `at_test_case`: Issues with test logic, assertions, or test case implementation.
    - `at_requirements`: Issues with requirement specification, clarity, or completeness.
    - `at_source_code`: Issues are not from at_test_case or at_requirements.

- **Action suggestions:** Recommendations that LogRoca provides for fixing the detected test failure.

- **Rationale:** LogRoca’s reasoning behind its analysis, when identifying and predicting root cause, root cause origin, and suggested actions.

---

Please feel free to contact me if you need any additional information.

With best regards,  
Rahmanu <rahmanu.hermawan@mdu.se>
