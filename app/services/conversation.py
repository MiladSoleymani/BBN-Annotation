"""Conversation data loading and saving services."""

import json
import copy
from datetime import datetime
import streamlit as st
from config import SCHEMA_PATH, SAMPLES_DIR


def load_schema():
    """Load annotation schema from JSON file."""
    if SCHEMA_PATH.exists():
        try:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            st.error(f"Error parsing schema file: {e}")
            return None
        except IOError as e:
            st.error(f"Error reading schema file: {e}")
            return None
    return None


def load_conversations():
    """Load all conversation files from the samples directory."""
    conversations = []
    if SAMPLES_DIR.exists():
        for file in sorted(SAMPLES_DIR.glob("*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    conv = json.load(f)
                    conv["filename"] = file.name
                    conv["filepath"] = str(file)
                    conversations.append(conv)
            except json.JSONDecodeError as e:
                st.warning(f"Skipping invalid JSON file {file.name}: {e}")
            except IOError as e:
                st.warning(f"Error reading {file.name}: {e}")
    return conversations


def save_conversation(conversation, filepath=None):
    """Save conversation with annotations to JSON file."""
    if filepath is None:
        filepath = (
            SAMPLES_DIR
            / f"annotated_{conversation.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)
        return filepath
    except IOError as e:
        st.error(f"Error saving file: {e}")
        return None


def merge_annotations_to_conversation(conversation):
    """Merge current session annotations into the conversation object."""
    for turn in conversation.get("turns", []):
        turn_id = turn["turn_id"]
        if turn_id in st.session_state.current_annotations:
            if "annotations" not in turn:
                turn["annotations"] = {}

            # Ensure spans and relations keys exist
            if "spans" not in turn["annotations"]:
                turn["annotations"]["spans"] = []
            if "relations" not in turn["annotations"]:
                turn["annotations"]["relations"] = []

            # Merge spans
            existing_span_ids = {s["span_id"] for s in turn["annotations"]["spans"]}
            for span in st.session_state.current_annotations[turn_id].get("spans", []):
                if span["span_id"] not in existing_span_ids:
                    turn["annotations"]["spans"].append(span)

            # Merge relations
            existing_rel_ids = {
                r.get("relation_id") for r in turn["annotations"]["relations"]
            }
            for rel in st.session_state.current_annotations[turn_id].get("relations", []):
                if rel.get("relation_id") not in existing_rel_ids:
                    turn["annotations"]["relations"].append(rel)

            # Set SPIKES stage
            if st.session_state.current_annotations[turn_id].get("spikes_stage"):
                turn["annotations"]["spikes_stage"] = st.session_state.current_annotations[turn_id]["spikes_stage"]

    return conversation


def load_existing_annotations(conversation):
    """Load existing annotations from conversation into session state."""
    st.session_state.current_annotations = {}

    for turn in conversation.get("turns", []):
        turn_id = turn["turn_id"]
        annotations = turn.get("annotations", {})

        if annotations:
            # Use deepcopy to avoid modifying original data
            st.session_state.current_annotations[turn_id] = {
                "spans": copy.deepcopy(annotations.get("spans", [])),
                "relations": copy.deepcopy(annotations.get("relations", [])),
                "spikes_stage": annotations.get("spikes_stage"),
            }
