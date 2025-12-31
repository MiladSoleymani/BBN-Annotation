"""Data service that provides a unified interface for JSON and database backends."""

import json
from pathlib import Path
from typing import Optional
import streamlit as st

from config import USE_DATABASE, SAMPLES_DIR, SCHEMA_PATH


def _use_db() -> bool:
    """Check if database should be used."""
    return USE_DATABASE


# ============== SCHEMA ==============

def load_schema() -> Optional[dict]:
    """Load annotation schema from JSON file."""
    if SCHEMA_PATH.exists():
        try:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error loading schema: {e}")
    return None


# ============== CONVERSATIONS ==============

def load_conversations() -> list[dict]:
    """Load all conversations (from database or JSON files)."""
    if _use_db():
        return _load_conversations_from_db()
    return _load_conversations_from_json()


def _load_conversations_from_db() -> list[dict]:
    """Load conversations from database."""
    try:
        from database import init_db, get_all_conversations, get_turns_by_conversation

        init_db()
        conversations = []

        for conv in get_all_conversations():
            turns = get_turns_by_conversation(conv.id)
            conv.turns = turns
            conv_dict = conv.to_dict()
            conv_dict["filepath"] = conv.source_file
            conv_dict["filename"] = Path(conv.source_file).name if conv.source_file else f"{conv.external_id}.json"
            conversations.append(conv_dict)

        return conversations
    except Exception as e:
        st.warning(f"Database error, falling back to JSON: {e}")
        return _load_conversations_from_json()


def _load_conversations_from_json() -> list[dict]:
    """Load conversations from JSON files."""
    conversations = []
    if SAMPLES_DIR.exists():
        for file in sorted(SAMPLES_DIR.glob("*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    conv = json.load(f)
                    conv["filename"] = file.name
                    conv["filepath"] = str(file)
                    conversations.append(conv)
            except (json.JSONDecodeError, IOError) as e:
                st.warning(f"Skipping {file.name}: {e}")
    return conversations


def get_conversation_by_id(conv_id: str) -> Optional[dict]:
    """Get a specific conversation by ID."""
    if _use_db():
        try:
            from database import get_conversation_by_external_id, get_full_conversation_with_annotations

            conv = get_conversation_by_external_id(conv_id)
            if conv:
                full_conv = get_full_conversation_with_annotations(conv.id)
                return full_conv.to_dict() if full_conv else None
        except Exception:
            pass

    # Fallback to JSON
    for conv in _load_conversations_from_json():
        if conv.get("id") == conv_id:
            return conv
    return None


# ============== SAVE ANNOTATIONS ==============

def save_annotations(conversation: dict, annotations: dict, expert_id: int = None) -> bool:
    """Save annotations (to database and/or JSON file)."""
    success = True

    if _use_db():
        success = _save_annotations_to_db(conversation, annotations, expert_id)

    # Also save to JSON (as backup / for compatibility)
    _save_annotations_to_json(conversation, annotations)

    return success


def _save_annotations_to_db(conversation: dict, annotations: dict, expert_id: int = None) -> bool:
    """Save annotations to database."""
    try:
        from database import (
            get_conversation_by_external_id,
            save_session_annotations,
            import_conversation_from_json,
        )

        conv_id = conversation.get("id")
        db_conv = get_conversation_by_external_id(conv_id)

        if not db_conv:
            # Import conversation first
            db_conv = import_conversation_from_json(conversation)

        if db_conv:
            save_session_annotations(db_conv.id, annotations, expert_id)
            return True

    except Exception as e:
        st.error(f"Database save error: {e}")

    return False


def _save_annotations_to_json(conversation: dict, annotations: dict) -> bool:
    """Save annotations to JSON file."""
    try:
        # Merge annotations into conversation
        merged = _merge_annotations(conversation.copy(), annotations)

        filepath = conversation.get("filepath")
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
            return True
    except IOError as e:
        st.error(f"JSON save error: {e}")

    return False


def _merge_annotations(conversation: dict, annotations: dict) -> dict:
    """Merge session annotations into conversation dict."""
    for turn in conversation.get("turns", []):
        turn_id = turn["turn_id"]
        if turn_id in annotations:
            if "annotations" not in turn:
                turn["annotations"] = {}

            turn_annotations = annotations[turn_id]

            # Merge spans
            existing_spans = {s["span_id"] for s in turn["annotations"].get("spans", [])}
            if "spans" not in turn["annotations"]:
                turn["annotations"]["spans"] = []
            for span in turn_annotations.get("spans", []):
                if span["span_id"] not in existing_spans:
                    turn["annotations"]["spans"].append(span)

            # Merge relations
            existing_rels = {r.get("relation_id") for r in turn["annotations"].get("relations", [])}
            if "relations" not in turn["annotations"]:
                turn["annotations"]["relations"] = []
            for rel in turn_annotations.get("relations", []):
                if rel.get("relation_id") not in existing_rels:
                    turn["annotations"]["relations"].append(rel)

            # Set SPIKES stage
            if turn_annotations.get("spikes_stage"):
                turn["annotations"]["spikes_stage"] = turn_annotations["spikes_stage"]

    return conversation


# ============== LOAD EXISTING ANNOTATIONS ==============

def load_existing_annotations(conversation: dict, expert_id: int = None) -> dict:
    """Load existing annotations for a conversation."""
    annotations = {}

    if _use_db():
        annotations = _load_annotations_from_db(conversation, expert_id)
        if annotations:
            return annotations

    # Fallback to JSON annotations
    return _load_annotations_from_json(conversation)


def _load_annotations_from_db(conversation: dict, expert_id: int = None) -> dict:
    """Load annotations from database."""
    try:
        from database import (
            get_conversation_by_external_id,
            get_turns_by_conversation,
            get_span_annotations,
            get_relations,
            get_spikes_annotation,
        )

        conv_id = conversation.get("id")
        db_conv = get_conversation_by_external_id(conv_id)

        if not db_conv:
            return {}

        annotations = {}
        turns = get_turns_by_conversation(db_conv.id)

        for turn in turns:
            spans = get_span_annotations(turn.id, expert_id)
            relations = get_relations(turn.id, expert_id)
            spikes = get_spikes_annotation(turn.id, expert_id)

            if spans or relations or spikes:
                annotations[turn.turn_number] = {
                    "spans": [s.to_dict() for s in spans],
                    "relations": [r.to_dict() for r in relations],
                    "spikes_stage": spikes.stage if spikes else None,
                }

        return annotations

    except Exception as e:
        st.warning(f"Error loading from database: {e}")
        return {}


def _load_annotations_from_json(conversation: dict) -> dict:
    """Load annotations from JSON conversation."""
    annotations = {}

    for turn in conversation.get("turns", []):
        turn_id = turn["turn_id"]
        turn_annotations = turn.get("annotations", {})

        if turn_annotations:
            annotations[turn_id] = {
                "spans": [s.copy() for s in turn_annotations.get("spans", [])],
                "relations": [r.copy() for r in turn_annotations.get("relations", [])],
                "spikes_stage": turn_annotations.get("spikes_stage"),
            }

    return annotations


# ============== EXPERTS ==============

def get_current_expert() -> Optional[dict]:
    """Get current expert from session state or create default."""
    if "current_expert" not in st.session_state:
        if _use_db():
            try:
                from database import get_or_create_expert

                expert = get_or_create_expert("Default Expert")
                st.session_state.current_expert = {
                    "id": expert.id,
                    "name": expert.name,
                }
            except Exception:
                st.session_state.current_expert = {"id": None, "name": "Default"}
        else:
            st.session_state.current_expert = {"id": None, "name": "Default"}

    return st.session_state.current_expert


def get_all_experts() -> list[dict]:
    """Get all experts."""
    if _use_db():
        try:
            from database import get_all_experts as db_get_all_experts

            experts = db_get_all_experts()
            return [{"id": e.id, "name": e.name, "role": e.role} for e in experts]
        except Exception:
            pass

    return [{"id": None, "name": "Default", "role": "annotator"}]
