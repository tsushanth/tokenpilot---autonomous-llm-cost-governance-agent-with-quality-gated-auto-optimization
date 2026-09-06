from tokenpilot.models import Task
from tokenpilot.optimizer import compress_prompt, generate_candidate
from tokenpilot.providers import CHEAP_MODEL, PRICE_TABLE


def test_compress_prompt_shrinks_word_count():
    original = (
        "Please carefully and politely answer the customer's question "
        "in order to resolve their issue. Kindly be concise."
    )
    compressed = compress_prompt(original)
    assert len(compressed.split()) < len(original.split())


def test_compress_prompt_preserves_placeholder():
    original = "Please kindly answer the question: {input}"
    compressed = compress_prompt(original)
    assert "{input}" in compressed


def test_generate_candidate_routes_to_cheap_tier():
    task = Task(
        name="t",
        baseline_model="claude-opus-5",
        prompt_template="Please kindly simply help the user in order to solve their problem.",
        quality_tolerance=0.1,
        eval_cases=[],
    )
    candidate = generate_candidate(task)

    assert candidate["model"] == CHEAP_MODEL
    assert candidate["model"] != task.baseline_model
    assert PRICE_TABLE[candidate["model"]]["tier"] == "cheap"
    assert len(candidate["prompt_template"].split()) < len(task.prompt_template.split())
