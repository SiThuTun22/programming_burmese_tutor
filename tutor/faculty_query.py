"""Faculty name hints (Myanmar + English) and retrieval query expansion for AAA RAG."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _FacultyProfile:
    hints: tuple[str, ...]
    retrieval_terms: str
    canonical_title: str


_PROFILES: tuple[_FacultyProfile, ...] = (
    _FacultyProfile(
        hints=(
            "cynthia",
            "cynthida",
            "sin thi yar",
            "sinthi yar",
            "စင်သီယာ",
            "စင်သီယာမြင့်",
            "ဒေါက်တာစင်သီယာ",
            "ဒေါ်စင်သီယာ",
        ),
        retrieval_terms="Dr. Cynthia Myint Dr. Sin Thi Yar Myint MIIT professor faculty",
        canonical_title="Dr Cynthia Myint",
    ),
    _FacultyProfile(
        hints=(
            "aye aye thant",
            "ayeaye thant",
            "အဲဘီရွန်းး",
            "အဲဘီရွန်း",
        ),
        retrieval_terms="Dr. Aye Aye Thant MIIT faculty",
        canonical_title="Dr Aye Aye Thant",
    ),
    _FacultyProfile(
        hints=(
            "kyawt kyawt htay",
            "kyawt htay",
            "ကျော်ကျော်ထက်",
        ),
        retrieval_terms="Dr. Kyawt Kyawt Htay MIIT faculty",
        canonical_title="Dr Kyawt Kyawt Htay",
    ),
    _FacultyProfile(
        hints=(
            "phyu thwe",
            "phyuthwe",
            "ဖြူသွေး",
        ),
        retrieval_terms="Dr. Phyu Thwe MIIT faculty",
        canonical_title="Dr Phyu Thwe",
    ),
    _FacultyProfile(
        hints=(
            "tin moh",
            "moh lwin",
            "tin moh moh lwin",
            "တင်မိုး",
            "မိုးလွင်",
        ),
        retrieval_terms="Dr. Tin Moh Moh Lwin MIIT faculty",
        canonical_title="Dr Tin Moh Moh Lwin",
    ),
    _FacultyProfile(
        hints=(
            "zar chi",
            "su su hlaing",
            "zar chi su su hlaing",
            "ဇာချီ",
            "စုစုလှိုင်",
        ),
        retrieval_terms="Dr. Zar Chi Su Su Hlaing MIIT faculty",
        canonical_title="Dr Zar Chi Su Su Hlaing",
    ),
)

GENERIC_FACULTY_HINTS: tuple[str, ...] = (
    "teacher",
    "professor",
    "faculty",
    "lecturer",
    "staff",
    "dr.",
    "ပါမောက္ခ",
    "ဆရာ",
    "ဆရာမ",
    "ဆရာ့",
    "ဒေါက်တာ",
    "ဘယ်သူ",
    "who is",
)

RESEARCH_HINTS: tuple[str, ...] = (
    "research",
    "paper",
    "papers",
    "publication",
    "journal",
    "thesis",
    "သုတေသန",
    "စာတမ်း",
    "စာတမ်းများ",
    "သုတေသနစာတမ်း",
)


def looks_like_research_question(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    for hint in RESEARCH_HINTS:
        if hint in lowered or hint in stripped:
            return True
    return False


def _matches(text: str, hint: str) -> bool:
    if not hint:
        return False
    if hint in text:
        return True
    return hint in text.lower()


def matched_faculty_profile(text: str) -> _FacultyProfile | None:
    """First known MIIT faculty profile matching the text, if any."""
    stripped = (text or "").strip()
    if not stripped:
        return None
    for profile in _PROFILES:
        for hint in profile.hints:
            if _matches(stripped, hint):
                return profile
    return None


def canonical_title_for_text(text: str) -> str | None:
    profile = matched_faculty_profile(text)
    if profile is None:
        return None
    return profile.canonical_title


def faculty_profile_matched(text: str) -> bool:
    """True when the question names a known MIIT faculty member (any script)."""
    return matched_faculty_profile(text) is not None


def faculty_routes_for_question(text: str) -> bool:
    """True when AAA should enable ROUTE_FACULTY retrieval."""
    stripped = (text or "").strip()
    if not stripped:
        return False
    if faculty_profile_matched(stripped):
        return True
    lowered = stripped.lower()
    for hint in GENERIC_FACULTY_HINTS:
        if hint in lowered or hint in stripped:
            return True
    return False


def _retrieval_terms_for_text(text: str) -> list[str]:
    extras: list[str] = []
    for profile in _PROFILES:
        for hint in profile.hints:
            if _matches(text, hint):
                extras.append(profile.retrieval_terms)
                break
    return extras


def expand_faculty_retrieval_query(text: str) -> str:
    """Append English retrieval terms for embed/retrieve; keeps original question text."""
    stripped = (text or "").strip()
    if not stripped:
        return stripped
    extras = _retrieval_terms_for_text(stripped)
    if not extras:
        return stripped
    return stripped + "\n" + " ".join(extras)


def expand_faculty_retrieval_query_with_history(
    user_content: str,
    message_history: str,
) -> str:
    """Expand embed query using the current ask and prior chat when it is a faculty follow-up."""
    stripped = (user_content or "").strip()
    history = (message_history or "").strip()
    base = expand_faculty_retrieval_query(stripped)
    if faculty_profile_matched(stripped):
        if looks_like_research_question(stripped):
            return base + "\n research papers publications journal cynthia-paper"
        return base
    if not history:
        return base
    history_terms = _retrieval_terms_for_text(history)
    if not history_terms:
        return base
    from tutor.router import looks_like_followup

    if not looks_like_followup(stripped) and not looks_like_research_question(stripped):
        return base
    merged = base + "\n" + " ".join(history_terms)
    if looks_like_research_question(stripped):
        merged = merged + " research papers publications segmentation POS MERAL"
    return merged


def faculty_routes_for_thread(user_content: str, message_history: str) -> bool:
    """Faculty retrieval when the ask or recent chat is about a known teacher."""
    if faculty_routes_for_question(user_content):
        return True
    history = (message_history or "").strip()
    if not history:
        return False
    if faculty_profile_matched(history) and (
        looks_like_research_question(user_content) or _followup_needs_faculty(user_content)
    ):
        return True
    return False


def _followup_needs_faculty(user_content: str) -> bool:
    from tutor.router import looks_like_followup

    return looks_like_followup(user_content)
