"""Chat session API read shape."""

from datetime import datetime, timezone
import uuid

from app.db.enums import ChatSessionStatus, TutorAvatar, TutorTone
from app.db.models import ChatSession
from app.routes.mappers import to_session_read


def test_to_session_read_includes_activity_fields() -> None:
    owner_id = uuid.uuid4()
    created = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    last_user = datetime(2026, 1, 2, 8, 30, tzinfo=timezone.utc)
    session = ChatSession(
        id=uuid.uuid4(),
        title='Cynthia papers',
        tutor_tone=TutorTone.SOCRATIC,
        tutor_avatar=TutorAvatar.FEMALE,
        status=ChatSessionStatus.ACTIVE,
        owner_id=owner_id,
        created_at=created,
    )
    read = to_session_read(session, last_user_message_at=last_user)
    assert read.created_at == created
    assert read.last_user_message_at == last_user
