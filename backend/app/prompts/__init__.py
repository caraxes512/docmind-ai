from app.prompts.base import PromptSpec
from app.prompts.repository_analyzer_prompt import REPOSITORY_ANALYZER_PROMPT
from app.prompts.readme_agent_prompt import README_AGENT_PROMPT
from app.prompts.api_doc_agent_prompt import API_DOC_AGENT_PROMPT
from app.prompts.function_doc_agent_prompt import FUNCTION_DOC_AGENT_PROMPT
from app.prompts.architecture_agent_prompt import ARCHITECTURE_AGENT_PROMPT
from app.prompts.diagram_agent_prompt import DIAGRAM_AGENT_PROMPT
from app.prompts.database_doc_agent_prompt import DATABASE_DOC_AGENT_PROMPT
from app.prompts.reviewer_agent_prompt import REVIEWER_AGENT_PROMPT
from app.prompts.chat_agent_prompt import CHAT_AGENT_PROMPT
from app.prompts.commit_message_prompt import COMMIT_MESSAGE_PROMPT
from app.prompts.pr_description_prompt import PR_DESCRIPTION_PROMPT
from app.prompts.release_notes_prompt import RELEASE_NOTES_PROMPT
from app.prompts.changelog_prompt import CHANGELOG_PROMPT

__all__ = [
    "PromptSpec",
    "REPOSITORY_ANALYZER_PROMPT",
    "README_AGENT_PROMPT",
    "API_DOC_AGENT_PROMPT",
    "FUNCTION_DOC_AGENT_PROMPT",
    "ARCHITECTURE_AGENT_PROMPT",
    "DIAGRAM_AGENT_PROMPT",
    "DATABASE_DOC_AGENT_PROMPT",
    "REVIEWER_AGENT_PROMPT",
    "CHAT_AGENT_PROMPT",
    "COMMIT_MESSAGE_PROMPT",
    "PR_DESCRIPTION_PROMPT",
    "RELEASE_NOTES_PROMPT",
    "CHANGELOG_PROMPT",
]
