from __future__ import annotations

from tutor.faculty_query import faculty_routes_for_question, faculty_routes_for_thread

ROUTE_FACULTY = 'faculty'
ROUTE_CAMPUS = 'campus'
ROUTE_COURSES = 'courses'
ROUTE_PDF = 'pdf'
ROUTE_PROGRAMMING = 'programming'

_FACULTY_HINTS = [
    'teacher',
    'professor',
    'faculty',
    'lecturer',
    'staff',
    'dr.',
    'cynthia',
    'sin thi yar',
    'kyawt',
    'htay',
    'thant',
    'aye aye',
    'phyu thwe',
    'thwe',
    'tin moh',
    'moh lwin',
    'zar chi',
    'zarchi',
    'su su hlaing',
    'ပါမောက္ခ',
    'ဆရာ',
    'ဆရာမ',
    'ဆရာ့',
]

_CAMPUS_HINTS = [
    'miit',
    'campus',
    'institute',
    'mandalay',
    'hostel',
    'university',
    'college',
    'admission',
    'campus',
    'rector',
    'iiit',
    'chanmyathazi',
    'မြန်မာနိုင်ငံ',
    'မန္တလေး',
]

_PROGRAMMING_HINTS = [
    'binary search',
    'algorithm',
    'python',
    'def ',
    'class ',
    'javascript',
    'react',
    'sql',
    'loop',
    'code',
    'ohm',
    'kirchhoff',
    'function',
    'variable',
    'array',
    'pointer',
    'recursion',
    'ကုဒ်',
    'ပရိုဂရမ်',
]

_COURSE_HINTS = [
    'course',
    'handout',
    'syllabus',
    'lecture',
    'module',
    'subject',
    'assignment',
    'catalog',
    'cse',
    'ece',
    'electronics',
    'communications',
    'b.e.',
    'hons',
    'semester',
    'elective',
    'capstone',
    'ဘာသာရပ်',
    'သင်ခန်းစာ',
]


def _has_hint(query_lower: str, hints: list[str]) -> bool:
    for hint in hints:
        if hint in query_lower:
            return True
    return False


def classify_routes(
    user_content: str,
    document_context: str,
    message_history: str = '',
) -> list[str]:
    query_lower = user_content.lower()
    routes: list[str] = []

    if (
        _has_hint(query_lower, _FACULTY_HINTS)
        or faculty_routes_for_question(user_content)
        or faculty_routes_for_thread(user_content, message_history)
    ):
        routes.append(ROUTE_FACULTY)
    if _has_hint(query_lower, _CAMPUS_HINTS):
        routes.append(ROUTE_CAMPUS)
    if _has_hint(query_lower, _COURSE_HINTS):
        routes.append(ROUTE_COURSES)
    if _has_hint(query_lower, _PROGRAMMING_HINTS):
        routes.append(ROUTE_PROGRAMMING)

    has_document = document_context != '(none)' and len(document_context.strip()) > 0
    if has_document:
        routes.append(ROUTE_PDF)

    unique: list[str] = []
    for route in routes:
        if route not in unique:
            unique.append(route)
    return unique
