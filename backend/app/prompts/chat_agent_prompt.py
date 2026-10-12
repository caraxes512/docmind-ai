"""Prompt spec for the Repository Chat Agent — RAG-grounded Q&A over an
indexed repository. This agent's graph is retrieval -> prompt construction
-> generation -> citation extraction (detailed in Step 9 — RAG Pipeline);
this file defines the generation-step prompt only."""

from app.prompts.base import PromptSpec

CHAT_AGENT_PROMPT = PromptSpec(
    agent_name="repository_chat_agent",
    system_prompt=(
        "You are a codebase assistant answering questions about a specific repository. Answer ONLY "
        "using the provided code excerpts — if the excerpts don't contain enough information to "
        "answer confidently, say so explicitly rather than speculating from general programming "
        "knowledge. Always reference which file(s) your answer is based on. If the question asks "
        "about something not represented in the excerpts (e.g. 'how does payment work' in a repo "
        "with no payment-related code), state plainly that you found no matching code rather than "
        "describing how payment systems work in general."
    ),
    developer_prompt_template=(
        "Conversation history (most recent last):\n{conversation_history}\n\n"
        "Retrieved code excerpts (ranked by relevance):\n{retrieved_chunks_json}\n\n"
        "User question: {user_question}\n\n"
        "Answer the question grounded in the excerpts above. End your answer with a 'Sources' list "
        "of the file paths you actually used (omit any excerpt you didn't rely on)."
    ),
    expected_inputs=["conversation_history", "retrieved_chunks_json", "user_question"],
    expected_output_schema=(
        "Plain text answer followed by a 'Sources' section — parsed into "
        "{answer_text: string, cited_file_paths: string[]} by the Chat Service, which cross-checks "
        "cited_file_paths against retrieved_chunks_json to build the Message.citations field"
    ),
    validation_rules=[
        "Every path listed under 'Sources' must correspond to a file_path present in "
        "retrieved_chunks_json — paths not in the retrieved set are dropped from citations "
        "rather than trusted at face value",
        "If retrieved_chunks_json is empty (no embeddings matched above the similarity threshold), "
        "skip the LLM call and return a fixed response stating no relevant code was found — avoids "
        "an ungrounded hallucinated answer when retrieval genuinely found nothing",
    ],
    failure_recovery=(
        "On LLM error (timeout, rate limit): retry once with exponential backoff (2s). On second "
        "failure: return a graceful error message as the assistant Message ('I couldn't generate an "
        "answer right now — please try again') rather than leaving the chat waiting indefinitely; "
        "the user_message is still persisted either way so the question isn't lost."
    ),
)
