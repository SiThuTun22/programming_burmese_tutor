from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentTerm(BaseModel):
    term: str = Field(description='Important term or name from the document, in English')
    definition: str = Field(
        description=(
            'One short, direct Myanmar sentence. '
            'Keep computer science and programming words in English. '
            'Do not use ရှင်, ဗျာ, ခင်ဗျာ, ကျွန်မ, or ကျွန်တော်.'
        ),
    )


class DocumentTermsResult(BaseModel):
    terms: list[DocumentTerm] = Field(
        description='8 to 15 important terms or names from the document text',
    )
