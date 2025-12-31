"""Annotation CRUD operations."""

import uuid
import streamlit as st
from state import save_to_undo_history


def add_span_annotation(turn_id, text, start, end, label):
    """Add a span annotation. Returns span_id or None if duplicate."""
    if turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[turn_id] = {
            "spans": [],
            "relations": [],
            "spikes_stage": None,
        }

    # Check for duplicate (same text and label)
    existing_spans = st.session_state.current_annotations[turn_id]["spans"]
    for existing in existing_spans:
        if existing["text"] == text and existing["label"] == label:
            return None  # Duplicate found

    save_to_undo_history()

    span = {
        "span_id": f"span_{uuid.uuid4().hex[:8]}",
        "text": text,
        "start": start,
        "end": end,
        "label": label,
    }

    st.session_state.current_annotations[turn_id]["spans"].append(span)
    return span["span_id"]


def remove_span_annotation(turn_id, span_id):
    """Remove a span annotation and its related relations."""
    save_to_undo_history()

    if turn_id in st.session_state.current_annotations:
        # Remove the span
        st.session_state.current_annotations[turn_id]["spans"] = [
            s
            for s in st.session_state.current_annotations[turn_id]["spans"]
            if s["span_id"] != span_id
        ]
        # Also remove related relations
        st.session_state.current_annotations[turn_id]["relations"] = [
            r
            for r in st.session_state.current_annotations[turn_id]["relations"]
            if r["from"] != span_id and r["to"] != span_id
        ]


def add_relation(from_turn_id, from_span_id, to_turn_id, to_span_id, relation_type):
    """Add a relation between two spans. Returns relation_id."""
    save_to_undo_history()

    if from_turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[from_turn_id] = {
            "spans": [],
            "relations": [],
            "spikes_stage": None,
        }

    relation = {
        "relation_id": f"rel_{uuid.uuid4().hex[:8]}",
        "from": from_span_id,
        "to": to_span_id,
        "to_turn_id": to_turn_id,
        "type": relation_type,
    }

    st.session_state.current_annotations[from_turn_id]["relations"].append(relation)
    return relation["relation_id"]


def set_spikes_stage(turn_id, stage):
    """Set SPIKES stage for a turn."""
    save_to_undo_history()

    if turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[turn_id] = {
            "spans": [],
            "relations": [],
            "spikes_stage": None,
        }
    st.session_state.current_annotations[turn_id]["spikes_stage"] = stage
