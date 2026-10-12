from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.document_terms import DocumentTerm, DocumentTermsResult
from app.ai.errors import LlmUnavailableError
from app.ai.llm import invoke_llm
from app.services.documents.context import truncate_document_context

TERM_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'Extract 8 to 15 important terms or names from the document text. '
            'Keep each term name in English. '
            'Write each definition as one short, direct Myanmar sentence. '
            'Leave computer science and programming words in English inside the definition. '
            'Do not use ရှင်, ဗျာ, ခင်ဗျာ, ကျွန်မ, or ကျွန်တော်. Plain ပါ is allowed if needed. '
            'No greeting, no follow-up question, no extra politeness.',
        ),
        ('human', '{document_text}'),
    ]
)


async def extract_document_terms(extracted_text: str) -> list[DocumentTerm]:
    if len(extracted_text.strip()) == 0:
        return []

    def make_term_runnable(chat_model: ChatGoogleGenerativeAI):
        structured_model = chat_model.with_structured_output(DocumentTermsResult)
        term_chain = TERM_PROMPT | structured_model
        return term_chain

    payload = {'document_text': truncate_document_context(extracted_text)}

    result = await invoke_llm(make_term_runnable, payload)

    if isinstance(result, DocumentTermsResult):
        parsed = result
    elif isinstance(result, dict):
        parsed = DocumentTermsResult.model_validate(result)
    else:
        raise LlmUnavailableError('Gemini returned an unexpected document term response.')

    return parsed.terms
