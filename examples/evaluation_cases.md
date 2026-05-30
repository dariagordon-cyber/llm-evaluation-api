# Evaluation Cases

These examples show realistic scenarios for evaluating LLM-generated answers. They are illustrative test cases for API usage and error analysis, not human-validated benchmark results.

## Case 1: Good Answer

**Task:** Explain overfitting.

**Model answer:** Overfitting happens when a model learns the training data too closely, including noise or accidental patterns. It may perform very well on training examples but poorly on new data. Common ways to reduce overfitting include using more data, regularization, cross-validation, pruning, or simpler models.

**Evaluation mode:** `general_answer`

**Criteria:**

- `correctness` (0.5): Does the answer explain the concept accurately?
- `clarity` (0.3): Is the answer easy to understand?
- `completeness` (0.2): Does the answer mention generalization or unseen data?

**Expected error types:** None, or no major error types.

**Why this case matters:** A strong answer should receive a high score and `passed=true`. This case demonstrates the happy path for clear, complete, and mostly correct educational content.

## Case 2: Too Short / Incomplete Answer

**Task:** Explain underfitting.

**Model answer:** Underfitting is when a model is bad.

**Evaluation mode:** `general_answer`

**Criteria:**

- `correctness` (0.5): Does the answer explain underfitting accurately?
- `clarity` (0.2): Is the explanation understandable?
- `completeness` (0.3): Does the answer explain that the model is too simple and performs poorly on training and test data?

**Expected error types:** `missing_information`

**Why this case matters:** Short answers can be technically adjacent but not useful. This case helps test whether the evaluator identifies missing conceptual detail.

## Case 3: Hallucinated Answer

**Task:** Explain FastAPI.

**Model answer:** FastAPI is a JavaScript framework created by Google for building mobile apps. It uses the Angular compiler and runs only in the browser.

**Evaluation mode:** `educational_answer`

**Criteria:**

- `accuracy` (0.7): Does the answer correctly describe FastAPI as a Python web API framework?
- `clarity` (0.2): Is the answer easy to follow?
- `relevance` (0.1): Does the answer stay focused on FastAPI?

**Expected error types:** `factual_error` or `hallucination`

**Why this case matters:** LLM evaluation should catch confident but incorrect claims. This case is useful for testing factuality and hallucination labeling.

## Case 4: Constraint-Following Failure

**Task:** Explain gradient descent in exactly two sentences for a beginner.

**Model answer:** Gradient descent is an iterative first-order optimization algorithm based on differentiable objective functions, partial derivatives, and parameter updates along the negative gradient. It involves learning rates, convergence criteria, convexity assumptions, local minima, saddle points, stochastic variants, batch variants, and second-order comparisons. In production neural networks, it can interact with momentum, Adam, RMSprop, and scheduling heuristics in ways that require careful tuning.

**Evaluation mode:** `constraint_following`

**Criteria:**

- `constraint_adherence` (0.5): Does the answer use exactly two sentences?
- `beginner_clarity` (0.3): Is the answer understandable for a beginner?
- `conceptual_accuracy` (0.2): Does the answer accurately explain the main idea?

**Expected error types:** `constraint_violation`, possibly `unclear_explanation`

**Why this case matters:** Good answers are not only accurate; they must follow user constraints. This case tests whether the evaluator notices length and audience requirements.

## Case 5: Ambiguity-Handling Case

**Task:** Explain the bank problem.

**Model answer:** The bank problem is about how financial banks decide whether to approve loans, manage deposits, and handle customer accounts.

**Evaluation mode:** `ambiguity_handling`

**Criteria:**

- `ambiguity_awareness` (0.5): Does the answer recognize that "bank" could mean a financial institution or river bank?
- `clarification_behavior` (0.3): Does the answer ask for clarification or state assumptions?
- `usefulness` (0.2): Does the answer provide a helpful next step?

**Expected error types:** `unsupported_assumption` or `overconfident_answer`

**Why this case matters:** Ambiguous prompts require careful handling. A better answer would ask whether "bank" means a financial bank, a river bank, or a specific known problem.
