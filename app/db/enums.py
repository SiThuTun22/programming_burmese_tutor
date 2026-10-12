from __future__ import annotations

import enum


class TutorTone(enum.StrEnum):
    SOCRATIC = 'socratic'
    STRICT_ACADEMIC = 'strict_academic'


class TutorAvatar(enum.StrEnum):
    MALE = 'male'
    FEMALE = 'female'


class ChatSessionStatus(enum.StrEnum):
    ACTIVE = 'active'
    ARCHIVED = 'archived'


class MessageRole(enum.StrEnum):
    USER = 'user'
    ASSISTANT = 'assistant'
