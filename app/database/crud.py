"""CRUD operations for BBN Annotation Tool database."""

import json
import uuid
from typing import Optional
from database.connection import get_db
from database.models import (
    Expert,
    Conversation,
    Turn,
    SpanAnnotation,
    Relation,
    SpikesAnnotation,
)


# ============== EXPERTS ==============

def create_expert(name: str, email: str = None, role: str = "annotator") -> Expert:
    """Create a new expert."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO experts (name, email, role) VALUES (?, ?, ?)",
            (name, email, role)
        )
        expert_id = cursor.lastrowid
        return Expert(id=expert_id, name=name, email=email, role=role)


def get_expert(expert_id: int) -> Optional[Expert]:
    """Get expert by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experts WHERE id = ?", (expert_id,))
        row = cursor.fetchone()
        return Expert.from_row(row)


def get_expert_by_name(name: str) -> Optional[Expert]:
    """Get expert by name."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experts WHERE name = ?", (name,))
        row = cursor.fetchone()
        return Expert.from_row(row)


def get_all_experts() -> list[Expert]:
    """Get all experts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experts ORDER BY name")
        return [Expert.from_row(row) for row in cursor.fetchall()]


def get_or_create_expert(name: str, email: str = None) -> Expert:
    """Get existing expert or create new one."""
    expert = get_expert_by_name(name)
    if expert:
        return expert
    return create_expert(name, email)


# ============== CONVERSATIONS ==============

def create_conversation(
    external_id: str,
    scenario: str = None,
    language: str = "en",
    date: str = None,
    source_file: str = None,
    metadata: dict = None,
) -> Conversation:
    """Create a new conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata) if metadata else None
        cursor.execute(
            """INSERT INTO conversations
               (external_id, scenario, language, date, source_file, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (external_id, scenario, language, date, source_file, metadata_json)
        )
        conv_id = cursor.lastrowid
        return Conversation(
            id=conv_id,
            external_id=external_id,
            scenario=scenario,
            language=language,
            date=date,
            source_file=source_file,
            metadata_json=metadata_json,
        )


def get_conversation(conv_id: int) -> Optional[Conversation]:
    """Get conversation by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        return Conversation.from_row(row)


def get_conversation_by_external_id(external_id: str) -> Optional[Conversation]:
    """Get conversation by external ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE external_id = ?", (external_id,))
        row = cursor.fetchone()
        return Conversation.from_row(row)


def get_all_conversations() -> list[Conversation]:
    """Get all conversations."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations ORDER BY created_at DESC")
        return [Conversation.from_row(row) for row in cursor.fetchall()]


# ============== TURNS ==============

def create_turn(
    conversation_id: int,
    turn_number: int,
    speaker: str,
    text: str,
) -> Turn:
    """Create a new turn."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO turns (conversation_id, turn_number, speaker, text)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, turn_number, speaker, text)
        )
        turn_id = cursor.lastrowid
        return Turn(
            id=turn_id,
            conversation_id=conversation_id,
            turn_number=turn_number,
            speaker=speaker,
            text=text,
        )


def get_turn(turn_id: int) -> Optional[Turn]:
    """Get turn by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM turns WHERE id = ?", (turn_id,))
        row = cursor.fetchone()
        return Turn.from_row(row)


def get_turn_by_number(conversation_id: int, turn_number: int) -> Optional[Turn]:
    """Get turn by conversation ID and turn number."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM turns WHERE conversation_id = ? AND turn_number = ?",
            (conversation_id, turn_number)
        )
        row = cursor.fetchone()
        return Turn.from_row(row)


def get_turns_by_conversation(conversation_id: int) -> list[Turn]:
    """Get all turns for a conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM turns WHERE conversation_id = ? ORDER BY turn_number",
            (conversation_id,)
        )
        return [Turn.from_row(row) for row in cursor.fetchall()]


# ============== SPAN ANNOTATIONS ==============

def create_span_annotation(
    turn_id: int,
    text: str,
    start_pos: int,
    end_pos: int,
    label: str,
    expert_id: int = None,
    source: str = "manual",
    confidence: float = None,
    span_id: str = None,
) -> SpanAnnotation:
    """Create a new span annotation."""
    if span_id is None:
        span_id = f"span_{uuid.uuid4().hex[:8]}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO span_annotations
               (turn_id, expert_id, span_id, text, start_pos, end_pos, label, source, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, expert_id, span_id, text, start_pos, end_pos, label, source, confidence)
        )
        annotation_id = cursor.lastrowid
        return SpanAnnotation(
            id=annotation_id,
            turn_id=turn_id,
            expert_id=expert_id,
            span_id=span_id,
            text=text,
            start_pos=start_pos,
            end_pos=end_pos,
            label=label,
            source=source,
            confidence=confidence,
        )


def get_span_annotations(turn_id: int, expert_id: int = None) -> list[SpanAnnotation]:
    """Get span annotations for a turn, optionally filtered by expert."""
    with get_db() as conn:
        cursor = conn.cursor()
        if expert_id:
            cursor.execute(
                "SELECT * FROM span_annotations WHERE turn_id = ? AND expert_id = ?",
                (turn_id, expert_id)
            )
        else:
            cursor.execute(
                "SELECT * FROM span_annotations WHERE turn_id = ?",
                (turn_id,)
            )
        return [SpanAnnotation.from_row(row) for row in cursor.fetchall()]


def get_span_annotation_by_span_id(span_id: str) -> Optional[SpanAnnotation]:
    """Get span annotation by span_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM span_annotations WHERE span_id = ?", (span_id,))
        row = cursor.fetchone()
        return SpanAnnotation.from_row(row)


def delete_span_annotation(span_id: str) -> bool:
    """Delete a span annotation by span_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM span_annotations WHERE span_id = ?", (span_id,))
        # Also delete related relations
        cursor.execute(
            "DELETE FROM relations WHERE from_span_id = ? OR to_span_id = ?",
            (span_id, span_id)
        )
        return cursor.rowcount > 0


# ============== RELATIONS ==============

def create_relation(
    turn_id: int,
    from_span_id: str,
    to_span_id: str,
    relation_type: str,
    to_turn_id: int = None,
    expert_id: int = None,
    relation_id: str = None,
) -> Relation:
    """Create a new relation."""
    if relation_id is None:
        relation_id = f"rel_{uuid.uuid4().hex[:8]}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO relations
               (turn_id, expert_id, relation_id, from_span_id, to_span_id, to_turn_id, relation_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, expert_id, relation_id, from_span_id, to_span_id, to_turn_id, relation_type)
        )
        rel_id = cursor.lastrowid
        return Relation(
            id=rel_id,
            turn_id=turn_id,
            expert_id=expert_id,
            relation_id=relation_id,
            from_span_id=from_span_id,
            to_span_id=to_span_id,
            to_turn_id=to_turn_id,
            relation_type=relation_type,
        )


def get_relations(turn_id: int, expert_id: int = None) -> list[Relation]:
    """Get relations for a turn, optionally filtered by expert."""
    with get_db() as conn:
        cursor = conn.cursor()
        if expert_id:
            cursor.execute(
                "SELECT * FROM relations WHERE turn_id = ? AND expert_id = ?",
                (turn_id, expert_id)
            )
        else:
            cursor.execute(
                "SELECT * FROM relations WHERE turn_id = ?",
                (turn_id,)
            )
        return [Relation.from_row(row) for row in cursor.fetchall()]


def delete_relation(relation_id: str) -> bool:
    """Delete a relation by relation_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relations WHERE relation_id = ?", (relation_id,))
        return cursor.rowcount > 0


# ============== SPIKES ANNOTATIONS ==============

def set_spikes_annotation(
    turn_id: int,
    stage: str,
    expert_id: int = None,
) -> SpikesAnnotation:
    """Set SPIKES stage for a turn (upsert)."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Try to update existing
        cursor.execute(
            """INSERT INTO spikes_annotations (turn_id, expert_id, stage)
               VALUES (?, ?, ?)
               ON CONFLICT(turn_id, expert_id) DO UPDATE SET stage = ?""",
            (turn_id, expert_id, stage, stage)
        )
        return SpikesAnnotation(
            turn_id=turn_id,
            expert_id=expert_id,
            stage=stage,
        )


def get_spikes_annotation(turn_id: int, expert_id: int = None) -> Optional[SpikesAnnotation]:
    """Get SPIKES annotation for a turn."""
    with get_db() as conn:
        cursor = conn.cursor()
        if expert_id:
            cursor.execute(
                "SELECT * FROM spikes_annotations WHERE turn_id = ? AND expert_id = ?",
                (turn_id, expert_id)
            )
        else:
            cursor.execute(
                "SELECT * FROM spikes_annotations WHERE turn_id = ? ORDER BY created_at DESC LIMIT 1",
                (turn_id,)
            )
        row = cursor.fetchone()
        return SpikesAnnotation.from_row(row)


# ============== BULK OPERATIONS ==============

def get_full_conversation_with_annotations(
    conversation_id: int,
    expert_id: int = None,
) -> Optional[Conversation]:
    """Get conversation with all turns and annotations."""
    conv = get_conversation(conversation_id)
    if not conv:
        return None

    turns = get_turns_by_conversation(conversation_id)
    for turn in turns:
        spans = get_span_annotations(turn.id, expert_id)
        relations = get_relations(turn.id, expert_id)
        spikes = get_spikes_annotation(turn.id, expert_id)

        turn.annotations = {
            "spans": [s.to_dict() for s in spans],
            "relations": [r.to_dict() for r in relations],
            "spikes_stage": spikes.stage if spikes else None,
        }

    conv.turns = turns
    return conv


def save_session_annotations(
    conversation_id: int,
    annotations: dict,
    expert_id: int = None,
) -> bool:
    """Save session annotations to database.

    Args:
        conversation_id: Database conversation ID
        annotations: Dict of turn_number -> {spans, relations, spikes_stage}
        expert_id: Expert ID (optional)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        for turn_number, turn_data in annotations.items():
            # Get turn ID
            cursor.execute(
                "SELECT id FROM turns WHERE conversation_id = ? AND turn_number = ?",
                (conversation_id, int(turn_number))
            )
            row = cursor.fetchone()
            if not row:
                continue
            turn_id = row["id"]

            # Save spans
            for span in turn_data.get("spans", []):
                # Check if span already exists
                cursor.execute(
                    "SELECT id FROM span_annotations WHERE span_id = ?",
                    (span["span_id"],)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO span_annotations
                           (turn_id, expert_id, span_id, text, start_pos, end_pos, label, source)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            turn_id,
                            expert_id,
                            span["span_id"],
                            span["text"],
                            span["start"],
                            span["end"],
                            span["label"],
                            span.get("source", "manual"),
                        )
                    )

            # Save relations
            for rel in turn_data.get("relations", []):
                rel_id = rel.get("relation_id", f"rel_{uuid.uuid4().hex[:8]}")
                cursor.execute(
                    "SELECT id FROM relations WHERE relation_id = ?",
                    (rel_id,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO relations
                           (turn_id, expert_id, relation_id, from_span_id, to_span_id, to_turn_id, relation_type)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            turn_id,
                            expert_id,
                            rel_id,
                            rel["from"],
                            rel["to"],
                            rel.get("to_turn_id"),
                            rel["type"],
                        )
                    )

            # Save SPIKES stage
            spikes_stage = turn_data.get("spikes_stage")
            if spikes_stage:
                cursor.execute(
                    """INSERT INTO spikes_annotations (turn_id, expert_id, stage)
                       VALUES (?, ?, ?)
                       ON CONFLICT(turn_id, expert_id) DO UPDATE SET stage = ?""",
                    (turn_id, expert_id, spikes_stage, spikes_stage)
                )

        conn.commit()
        return True


def import_conversation_from_json(json_data: dict, source_file: str = None) -> Conversation:
    """Import a conversation from JSON format into the database."""
    external_id = json_data.get("id", f"conv_{uuid.uuid4().hex[:8]}")
    metadata = json_data.get("metadata", {})

    # Check if conversation already exists
    existing = get_conversation_by_external_id(external_id)
    if existing:
        return existing

    # Create conversation
    conv = create_conversation(
        external_id=external_id,
        scenario=metadata.get("scenario"),
        language=metadata.get("language", "en"),
        date=metadata.get("date"),
        source_file=source_file,
        metadata=metadata,
    )

    # Create turns
    for turn_data in json_data.get("turns", []):
        turn = create_turn(
            conversation_id=conv.id,
            turn_number=turn_data["turn_id"],
            speaker=turn_data["speaker"],
            text=turn_data["text"],
        )

        # Import existing annotations if present
        annotations = turn_data.get("annotations", {})

        for span in annotations.get("spans", []):
            create_span_annotation(
                turn_id=turn.id,
                text=span["text"],
                start_pos=span.get("start", 0),
                end_pos=span.get("end", len(span["text"])),
                label=span["label"],
                span_id=span.get("span_id"),
                source="imported",
            )

        for rel in annotations.get("relations", []):
            create_relation(
                turn_id=turn.id,
                from_span_id=rel["from"],
                to_span_id=rel["to"],
                relation_type=rel["type"],
                to_turn_id=rel.get("to_turn_id"),
                relation_id=rel.get("relation_id"),
            )

        if annotations.get("spikes_stage"):
            set_spikes_annotation(turn.id, annotations["spikes_stage"])

    return conv
