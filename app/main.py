import streamlit as st
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from datetime import datetime
import uuid

# Add parent directory to path for agent imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Page configuration
st.set_page_config(
    page_title="BBN Annotation Tool",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling - clean, minimal design
st.markdown(
    """
<style>
    /* Reduce default Streamlit spacing */
    .block-container {
        padding-top: 1rem;
    }
    .element-container {
        margin-bottom: 0;
    }
    /* Tighter info/caption spacing */
    .stAlert {
        margin-bottom: 0.25rem;
    }
    .stCaption {
        margin-top: 0;
        margin-bottom: 0.25rem;
    }
    hr {
        margin: 0.25rem 0;
    }
    /* Tighter button spacing */
    .stColumns {
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
    }

    /* Turn cards - Clean, minimal design */
    .patient-turn {
        background: #f8f4ff;
        padding: 16px 20px;
        border-radius: 8px;
        margin: 4px 0;
        border-left: 4px solid #8b5cf6;
    }
    .clinician-turn {
        background: #f0fdf4;
        padding: 16px 20px;
        border-radius: 8px;
        margin: 4px 0;
        border-left: 4px solid #22c55e;
    }
    .speaker-label {
        font-weight: 600;
        font-size: 0.85em;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
    }
    .patient-turn .speaker-label { color: #7c3aed; }
    .clinician-turn .speaker-label { color: #16a34a; }
    .turn-text {
        font-size: 1em;
        line-height: 1.6;
        color: #1e293b;
    }
    .annotation-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75em;
        margin: 2px;
        color: #1e293b;
        font-weight: 500;
    }
    .highlight-span {
        padding: 1px 4px;
        border-radius: 3px;
        font-weight: 500;
        color: #1e293b;
    }
    .annotation-section {
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid #e2e8f0;
        font-size: 0.85em;
    }

    /* Modal text display */
    .selectable-text {
        background: #f8fafc;
        padding: 16px;
        border-radius: 8px;
        margin: 10px 0;
        color: #1e293b;
        font-size: 1em;
        line-height: 1.7;
        border: 1px solid #e2e8f0;
        cursor: text;
        user-select: text;
    }

    /* AI suggestion cards */
    .ai-suggestion {
        background: #fffbeb;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border: 1px solid #fcd34d;
        color: #1e293b;
    }

    /* Relation items */
    .relation-item {
        background: #eff6ff;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 6px 0;
        border: 1px solid #bfdbfe;
        font-size: 0.9em;
        color: #1e40af;
        font-weight: 500;
    }
    .relation-item .rel-arrow {
        color: #64748b;
        margin: 0 8px;
    }
    .relation-item .rel-type {
        background: #dbeafe;
        padding: 2px 8px;
        border-radius: 4px;
        color: #1e40af;
    }

    /* Undo button styling */
    .undo-btn {
        background: #fef2f2;
        border: 1px solid #fecaca;
        color: #dc2626;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85em;
    }

    /* Clean button styles */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
    }

    /* Annotation count badge */
    .count-badge {
        background: #e0e7ff;
        color: #4338ca;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
        font-weight: 600;
    }

    /* Relations badge */
    .relations-badge {
        display: inline-block;
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
        border: 1px solid #93c5fd;
        margin-top: 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============== Data Loading Functions ==============


def load_schema():
    """Load annotation schema from JSON file."""
    schema_path = Path(__file__).parent.parent / "data" / "annotation_schema.json"
    if schema_path.exists():
        with open(schema_path, "r") as f:
            return json.load(f)
    return None


def load_conversations():
    """Load all conversation files from the samples directory."""
    samples_dir = Path(__file__).parent.parent / "data" / "samples"
    conversations = []
    if samples_dir.exists():
        for file in sorted(samples_dir.glob("*.json")):
            with open(file, "r") as f:
                conv = json.load(f)
                conv["filename"] = file.name
                conv["filepath"] = str(file)
                conversations.append(conv)
    return conversations


def save_conversation(conversation, filepath=None):
    """Save conversation with annotations to JSON file."""
    if filepath is None:
        samples_dir = Path(__file__).parent.parent / "data" / "samples"
        filepath = (
            samples_dir
            / f"annotated_{conversation.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    with open(filepath, "w") as f:
        json.dump(conversation, f, indent=2, ensure_ascii=False)

    return filepath


# ============== Color and Label Functions ==============


def get_label_color(label, schema=None):
    """Get color for a label from the schema."""
    color_map = {
        # Patient EOs - Warm colors for feelings, cool for others
        "explicit_feeling": "#FF6B6B",
        "implicit_feeling": "#FFA07A",
        "explicit_appreciation": "#20E3B2",
        "implicit_appreciation": "#7DFFCC",
        "explicit_judgement": "#74B9FF",
        "implicit_judgement": "#A8D8FF",
        # Clinician Elicitations
        "direct_elicitation_feeling": "#FFD93D",
        "indirect_elicitation_feeling": "#FFE66D",
        "direct_elicitation_appreciation": "#FFA94D",
        "indirect_elicitation_appreciation": "#FFBE76",
        "direct_elicitation_judgement": "#FF9FF3",
        "indirect_elicitation_judgement": "#FFB8E0",
        # Clinician Responses
        "acceptance_positive_regard_explicit_judgement": "#00D9A5",
        "acceptance_positive_regard_implicit_judgement": "#55EFC4",
        "acceptance_positive_regard_repetition": "#81ECEC",
        "acceptance_positive_regard_allowing": "#B8F5F1",
        "acceptance_neutral_support_appreciation": "#FDCB6E",
        "acceptance_neutral_support_judgement": "#FFE5A0",
        "sharing_feeling": "#E056FD",
        "sharing_appreciation": "#F0A1FF",
        "sharing_judgement": "#FFD1FF",
        "understanding_feeling": "#54A0FF",
        "understanding_appreciation": "#82CCFF",
        "understanding_judgement": "#B8E0FF",
        # SPIKES
        "setting": "#FF6B6B",
        "perception": "#FFA502",
        "invitation": "#FFD93D",
        "knowledge": "#2ED573",
        "empathy": "#54A0FF",
        "strategy": "#A55EEA",
    }
    return color_map.get(label, "#95A5A6")


def format_label_name(label):
    """Format label name for display."""
    return label.replace("_", " ").title()


def get_label_options():
    """Get all available label options organized by category."""
    return {
        "Patient EOs": {
            "Feelings": ["explicit_feeling", "implicit_feeling"],
            "Appreciation": ["explicit_appreciation", "implicit_appreciation"],
            "Judgement": ["explicit_judgement", "implicit_judgement"],
        },
        "Clinician Elicitations": {
            "Feelings": ["direct_elicitation_feeling", "indirect_elicitation_feeling"],
            "Appreciation": [
                "direct_elicitation_appreciation",
                "indirect_elicitation_appreciation",
            ],
            "Judgement": [
                "direct_elicitation_judgement",
                "indirect_elicitation_judgement",
            ],
        },
        "Clinician Responses - Acceptance": {
            "Positive Regard": [
                "acceptance_positive_regard_explicit_judgement",
                "acceptance_positive_regard_implicit_judgement",
                "acceptance_positive_regard_repetition",
                "acceptance_positive_regard_allowing",
            ],
            "Neutral Support": [
                "acceptance_neutral_support_appreciation",
                "acceptance_neutral_support_judgement",
            ],
        },
        "Clinician Responses - Sharing": {
            "Types": ["sharing_feeling", "sharing_appreciation", "sharing_judgement"]
        },
        "Clinician Responses - Understanding": {
            "Types": [
                "understanding_feeling",
                "understanding_appreciation",
                "understanding_judgement",
            ]
        },
        "SPIKES Stages": {
            "Stages": [
                "setting",
                "perception",
                "invitation",
                "knowledge",
                "empathy",
                "strategy",
            ]
        },
    }


# ============== Session State Initialization ==============


def init_session_state():
    """Initialize session state variables."""
    if "current_annotations" not in st.session_state:
        st.session_state.current_annotations = {}

    if "selected_turn" not in st.session_state:
        st.session_state.selected_turn = None

    if "selected_text" not in st.session_state:
        st.session_state.selected_text = ""

    if "pending_spans" not in st.session_state:
        st.session_state.pending_spans = []

    if "pending_relations" not in st.session_state:
        st.session_state.pending_relations = []

    if "ai_suggestions" not in st.session_state:
        st.session_state.ai_suggestions = []

    if "annotation_mode" not in st.session_state:
        st.session_state.annotation_mode = "view"

    # Track which dialog is open (to persist across reruns)
    if "open_dialog_turn_id" not in st.session_state:
        st.session_state.open_dialog_turn_id = None

    # Undo history stack
    if "undo_history" not in st.session_state:
        st.session_state.undo_history = []

    # Agent configuration
    if "agent_config" not in st.session_state:
        st.session_state.agent_config = {
            "provider": "openai",
            "model": "gpt-4o",
            "agent_type": "react",
            "api_key": os.getenv("OPENAI_API_KEY", ""),
        }


def save_to_undo_history():
    """Save current state to undo history."""
    import copy
    # Keep max 20 undo states
    if len(st.session_state.undo_history) >= 20:
        st.session_state.undo_history.pop(0)
    st.session_state.undo_history.append(
        copy.deepcopy(st.session_state.current_annotations)
    )


def undo_last_action():
    """Restore the previous annotation state."""
    if st.session_state.undo_history:
        st.session_state.current_annotations = st.session_state.undo_history.pop()
        return True
    return False


# ============== Agent Functions ==============


def get_agent_runner():
    """Get configured agent runner based on session state."""
    try:
        from agents.runner import AnnotationRunner

        config = st.session_state.agent_config

        # Determine API key based on provider
        api_key = config.get("api_key", "")
        if not api_key:
            if config["provider"] == "openai":
                api_key = os.getenv("OPENAI_API_KEY", "")
            else:
                api_key = os.getenv("ANTHROPIC_API_KEY", "")

        runner = AnnotationRunner(
            agent_type=config["agent_type"],
            provider=config["provider"],
            model=config["model"],
            api_key=api_key,
        )
        return runner
    except ImportError as e:
        st.error(f"Failed to import agents: {e}")
        return None
    except Exception as e:
        st.error(f"Failed to create agent runner: {e}")
        return None


def run_agent_on_turn(turn, context=""):
    """Run the agent on a single turn."""
    runner = get_agent_runner()
    if runner is None:
        return None

    try:
        result = runner.annotate_turn(turn, context)
        return result
    except Exception as e:
        st.error(f"Agent error: {e}")
        return None


def agent_result_to_suggestions(agent_result, turn_id):
    """Convert agent result to suggestion format for UI."""
    suggestions = []

    if agent_result is None:
        return suggestions

    # Handle TurnAnnotation directly
    if hasattr(agent_result, "spans"):
        for span in agent_result.spans:
            suggestions.append(
                {
                    "turn_id": turn_id,
                    "text": span.text,
                    "start": span.start,
                    "end": span.end,
                    "suggested_label": span.label,
                    "reasoning": span.reasoning,
                }
            )
        return suggestions

    # Handle AnnotationResult
    if hasattr(agent_result, "turns"):
        for turn in agent_result.turns:
            if turn.turn_id == turn_id:
                for span in turn.spans:
                    suggestions.append(
                        {
                            "turn_id": turn_id,
                            "text": span.text,
                            "start": span.start,
                            "end": span.end,
                            "suggested_label": span.label,
                            "reasoning": span.reasoning,
                        }
                    )

    return suggestions


# ============== Annotation Functions ==============


def add_span_annotation(turn_id, text, start, end, label):
    """Add a span annotation to the current annotations. Returns span_id or None if duplicate."""
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

    save_to_undo_history()  # Save state before modifying

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
    """Remove a span annotation."""
    save_to_undo_history()  # Save state before modifying

    if turn_id in st.session_state.current_annotations:
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
    """Add a relation between two spans."""
    save_to_undo_history()  # Save state before modifying

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
    """Set SPIKES stage for a clinician turn."""
    save_to_undo_history()  # Save state before modifying

    if turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[turn_id] = {
            "spans": [],
            "relations": [],
            "spikes_stage": None,
        }
    st.session_state.current_annotations[turn_id]["spikes_stage"] = stage


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
            existing_span_ids = {
                s["span_id"] for s in turn["annotations"]["spans"]
            }
            for span in st.session_state.current_annotations[turn_id].get("spans", []):
                if span["span_id"] not in existing_span_ids:
                    turn["annotations"]["spans"].append(span)

            # Merge relations
            existing_rel_ids = {
                r.get("relation_id") for r in turn["annotations"]["relations"]
            }
            for rel in st.session_state.current_annotations[turn_id].get(
                "relations", []
            ):
                if rel.get("relation_id") not in existing_rel_ids:
                    turn["annotations"]["relations"].append(rel)

            # Set SPIKES stage
            if st.session_state.current_annotations[turn_id].get("spikes_stage"):
                turn["annotations"]["spikes_stage"] = (
                    st.session_state.current_annotations[turn_id]["spikes_stage"]
                )

    return conversation


def load_existing_annotations(conversation):
    """Load existing annotations from conversation into session state."""
    st.session_state.current_annotations = {}

    for turn in conversation.get("turns", []):
        turn_id = turn["turn_id"]
        annotations = turn.get("annotations", {})

        if annotations:
            st.session_state.current_annotations[turn_id] = {
                "spans": annotations.get("spans", []).copy(),
                "relations": annotations.get("relations", []).copy(),
                "spikes_stage": annotations.get("spikes_stage"),
            }


# ============== UI Components ==============


@st.dialog("Annotate Turn", width="large")
def annotation_dialog(turn, schema, conversation):
    """Modal dialog for annotating a single turn."""
    turn_id = turn["turn_id"]
    speaker = turn["speaker"]
    text = turn["text"]

    # Header with speaker info
    speaker_icon = "🧑‍🦱" if speaker == "patient" else "👨‍⚕️"
    speaker_color = "#8b5cf6" if speaker == "patient" else "#22c55e"
    st.markdown(
        f'<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">'
        f'<span style="font-size: 1.5em;">{speaker_icon}</span>'
        f'<span style="font-size: 1.2em; font-weight: 600; color: {speaker_color};">{speaker.title()}</span>'
        f'<span style="color: #64748b; font-size: 0.9em;">Turn {turn_id}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Display the turn text with highlight hint
    st.markdown(
        f'<div class="selectable-text">{text}</div>',
        unsafe_allow_html=True,
    )
    st.caption("💡 Select text above and paste it below to annotate")

    # Two columns: Annotation tools | AI Suggestions
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### ✏️ Manual Annotation")

        # Text selection input with better UX
        selected_text = st.text_input(
            "Text to annotate:",
            key=f"modal_text_{turn_id}",
            placeholder="Paste selected text here...",
        )

        if selected_text:
            if selected_text in text:
                start_idx = text.find(selected_text)
                st.success(f"✓ Found at position {start_idx}")

                # Label selection - simplified
                st.markdown("**Choose label:**")

                # Filter labels based on speaker
                if speaker == "patient":
                    label_groups = {
                        "Feelings": ["explicit_feeling", "implicit_feeling"],
                        "Appreciation": ["explicit_appreciation", "implicit_appreciation"],
                        "Judgement": ["explicit_judgement", "implicit_judgement"],
                    }
                else:
                    label_groups = {
                        "Elicitations": [
                            "direct_elicitation_feeling", "indirect_elicitation_feeling",
                            "direct_elicitation_appreciation", "indirect_elicitation_appreciation",
                            "direct_elicitation_judgement", "indirect_elicitation_judgement",
                        ],
                        "Acceptance": [
                            "acceptance_positive_regard_explicit_judgement",
                            "acceptance_positive_regard_implicit_judgement",
                            "acceptance_positive_regard_repetition",
                            "acceptance_positive_regard_allowing",
                            "acceptance_neutral_support_appreciation",
                            "acceptance_neutral_support_judgement",
                        ],
                        "Sharing": ["sharing_feeling", "sharing_appreciation", "sharing_judgement"],
                        "Understanding": ["understanding_feeling", "understanding_appreciation", "understanding_judgement"],
                    }

                # Create a flat list for selectbox
                all_labels = []
                for group, labels in label_groups.items():
                    all_labels.extend(labels)

                selected_label = st.selectbox(
                    "Label:",
                    options=all_labels,
                    format_func=format_label_name,
                    key=f"modal_label_{turn_id}",
                )

                # Show color preview
                color = get_label_color(selected_label)
                st.markdown(
                    f'<span style="background-color: {color}; color: #1a1a2e; padding: 4px 12px; border-radius: 20px; font-weight: 600;">{format_label_name(selected_label)}</span>',
                    unsafe_allow_html=True,
                )

                if st.button("➕ Add Annotation", type="primary", key=f"modal_add_{turn_id}"):
                    result = add_span_annotation(
                        turn_id,
                        selected_text,
                        start_idx,
                        start_idx + len(selected_text),
                        selected_label,
                    )
                    if result:
                        st.success("Annotation added!")
                        st.rerun()
                    else:
                        st.warning("⚠️ This annotation already exists!")
            else:
                st.error("✗ Text not found in this turn")

        # SPIKES stage for clinician
        if speaker == "clinician":
            st.markdown("---")
            st.markdown("**SPIKES Stage:**")
            spikes_options = ["None", "setting", "perception", "invitation", "knowledge", "empathy", "strategy"]
            current_spikes = st.session_state.current_annotations.get(turn_id, {}).get("spikes_stage")

            selected_spikes = st.selectbox(
                "Stage:",
                spikes_options,
                index=spikes_options.index(current_spikes) if current_spikes in spikes_options else 0,
                key=f"modal_spikes_{turn_id}",
            )

            if selected_spikes != "None" and selected_spikes != current_spikes:
                if st.button("Set SPIKES Stage", key=f"modal_spikes_btn_{turn_id}"):
                    set_spikes_stage(turn_id, selected_spikes)
                    st.rerun()

    with col2:
        st.markdown("#### 🤖 AI Suggestions")

        # Build context from previous turns
        context_parts = []
        for t in conversation.get("turns", []):
            if t["turn_id"] < turn["turn_id"]:
                context_parts.append(f"{t['speaker'].upper()}: {t['text'][:100]}")
        context = "\n".join(context_parts[-5:])

        # Check API key
        config = st.session_state.agent_config
        has_api_key = bool(config.get("api_key")) or bool(
            os.getenv("OPENAI_API_KEY" if config["provider"] == "openai" else "ANTHROPIC_API_KEY")
        )

        if not has_api_key:
            st.warning("Configure API key in sidebar for AI suggestions.")
        else:
            st.caption(f"Using {config['agent_type'].upper()} with {config['model']}")

            if st.button("🔮 Generate Suggestions", key=f"modal_ai_{turn_id}"):
                with st.spinner("Analyzing..."):
                    result = run_agent_on_turn(turn, context)
                    if result:
                        st.session_state.ai_suggestions = agent_result_to_suggestions(result, turn_id)
                        st.rerun()

        # Display suggestions
        suggestions_for_turn = [s for s in st.session_state.ai_suggestions if s["turn_id"] == turn_id]

        if suggestions_for_turn:
            for i, suggestion in enumerate(suggestions_for_turn):
                color = get_label_color(suggestion["suggested_label"])
                st.markdown(
                    f"""<div style="background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%); padding: 10px; border-radius: 8px; margin: 8px 0; color: #1a1a2e;">
                    <strong>{format_label_name(suggestion['suggested_label'])}</strong><br>
                    <small>"{suggestion['text'][:50]}..."</small>
                    </div>""",
                    unsafe_allow_html=True,
                )

                c1, c2, _ = st.columns([1, 1, 4])
                with c1:
                    if st.button("✅ Accept", key=f"modal_accept_{turn_id}_{i}"):
                        result = add_span_annotation(
                            suggestion["turn_id"],
                            suggestion["text"],
                            suggestion.get("start", 0),
                            suggestion.get("end", len(suggestion["text"])),
                            suggestion["suggested_label"],
                        )
                        if result:
                            st.session_state.ai_suggestions = [
                                s for s in st.session_state.ai_suggestions
                                if not (s["turn_id"] == suggestion["turn_id"] and s["text"] == suggestion["text"])
                            ]
                            st.rerun()
                        else:
                            st.warning("⚠️ Already exists!")
                with c2:
                    if st.button("❌ Reject", key=f"modal_reject_{turn_id}_{i}"):
                        st.session_state.ai_suggestions = [
                            s for s in st.session_state.ai_suggestions
                            if not (s["turn_id"] == suggestion["turn_id"] and s["text"] == suggestion["text"])
                        ]
                        st.rerun()
        else:
            st.caption("No suggestions yet. Click Generate to get AI suggestions.")

    # Current annotations section
    st.markdown("---")

    # Header with undo button
    header_col1, header_col2, header_col3 = st.columns([3, 2, 1])
    with header_col1:
        st.markdown("#### 📋 Current Annotations")
    with header_col3:
        if st.session_state.undo_history:
            if st.button("↩️ Undo", key=f"modal_undo_{turn_id}"):
                undo_last_action()
                st.rerun()

    turn_annotations = st.session_state.current_annotations.get(turn_id, {"spans": [], "relations": []})

    if turn_annotations.get("spans"):
        for span in turn_annotations["spans"]:
            col_text, col_label, col_del = st.columns([3, 2, 1])
            with col_text:
                color = get_label_color(span["label"])
                st.markdown(
                    f'<span style="background-color: {color}; color: #1e293b; padding: 2px 8px; border-radius: 4px;">"{span["text"][:40]}{"..." if len(span["text"]) > 40 else ""}"</span>',
                    unsafe_allow_html=True,
                )
            with col_label:
                st.caption(format_label_name(span["label"]))
            with col_del:
                if st.button("🗑️ Del", key=f"modal_del_{span['span_id']}"):
                    remove_span_annotation(turn_id, span["span_id"])
                    st.rerun()
    else:
        st.caption("No annotations for this turn yet.")

    # Relations section
    st.markdown("---")
    st.markdown("#### 🔗 Link Relations")

    # Get all spans from this conversation for relation linking
    all_patient_spans = []
    all_clinician_spans = []

    for t in conversation.get("turns", []):
        t_id = t["turn_id"]
        t_speaker = t["speaker"]
        t_annotations = st.session_state.current_annotations.get(t_id, {"spans": []})
        for span in t_annotations.get("spans", []):
            span_info = {
                "turn_id": t_id,
                "span_id": span["span_id"],
                "text": span["text"][:30] + "..." if len(span["text"]) > 30 else span["text"],
                "label": span["label"],
                "display": f"T{t_id}: \"{span['text'][:25]}...\" [{format_label_name(span['label'])}]"
            }
            if t_speaker == "patient":
                all_patient_spans.append(span_info)
            else:
                all_clinician_spans.append(span_info)

    if all_patient_spans and all_clinician_spans:
        rel_col1, rel_col2 = st.columns(2)
        with rel_col1:
            from_options = ["Select patient EO..."] + [s["display"] for s in all_patient_spans]
            selected_from = st.selectbox("From (Patient EO):", from_options, key=f"rel_from_{turn_id}")
        with rel_col2:
            to_options = ["Select clinician response..."] + [s["display"] for s in all_clinician_spans]
            selected_to = st.selectbox("To (Clinician):", to_options, key=f"rel_to_{turn_id}")

        if selected_from != "Select patient EO..." and selected_to != "Select clinician response...":
            if st.button("🔗 Create Link", key=f"create_rel_{turn_id}"):
                from_span = next(s for s in all_patient_spans if s["display"] == selected_from)
                to_span = next(s for s in all_clinician_spans if s["display"] == selected_to)
                add_relation(
                    to_span["turn_id"],
                    to_span["span_id"],
                    from_span["turn_id"],
                    from_span["span_id"],
                    "response_to"
                )
                st.success("Relation created!")
                st.rerun()
    else:
        st.caption("Add patient and clinician annotations to create relations.")

    # Show existing relations
    if turn_annotations.get("relations"):
        st.markdown("**Existing relations:**")
        for rel in turn_annotations["relations"]:
            # Find the span texts for better display
            from_text = rel["from"]
            to_text = rel["to"]
            # Look up actual span text from all spans
            for s in all_clinician_spans:
                if s["span_id"] == rel["from"]:
                    from_text = f'"{s["text"]}"'
                    break
            for s in all_patient_spans:
                if s["span_id"] == rel["to"]:
                    to_text = f'"{s["text"]}"'
                    break
            st.markdown(
                f'<div class="relation-item">'
                f'<span style="color:#16a34a;">👨‍⚕️ {from_text}</span>'
                f'<span class="rel-arrow">→</span>'
                f'<span class="rel-type">{rel["type"].replace("_", " ")}</span>'
                f'<span class="rel-arrow">→</span>'
                f'<span style="color:#7c3aed;">🧑‍🦱 {to_text}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Close button
    st.markdown("---")
    if st.button("✓ Done", type="primary", use_container_width=True):
        st.session_state.open_dialog_turn_id = None
        st.rerun()


def render_turn_card(turn, schema, show_annotations=True):
    """Render a conversation turn card with annotate button."""
    text = turn["text"]
    speaker = turn["speaker"]
    turn_id = turn["turn_id"]

    # Get annotations
    original_annotations = turn.get("annotations", {})
    session_annotations = st.session_state.current_annotations.get(turn_id, {})

    # Combine spans
    spans = original_annotations.get("spans", []).copy()
    for span in session_annotations.get("spans", []):
        if span["span_id"] not in [s["span_id"] for s in spans]:
            spans.append(span)

    spikes_stage = session_annotations.get("spikes_stage") or original_annotations.get("spikes_stage")

    # Build highlighted text
    highlighted_text = text
    if show_annotations and spans:
        sorted_spans = sorted(spans, key=lambda x: x.get("start", 0), reverse=True)
        for span in sorted_spans:
            label = span.get("label", "")
            color = get_label_color(label, schema)
            span_text = span.get("text", "")
            if span_text in highlighted_text:
                highlighted_text = highlighted_text.replace(
                    span_text,
                    f'<span class="highlight-span" style="background-color: {color};" title="{format_label_name(label)}">{span_text}</span>',
                    1,
                )

    # Render the turn with clean styling
    turn_class = "patient-turn" if speaker == "patient" else "clinician-turn"
    speaker_icon = "🧑‍🦱" if speaker == "patient" else "👨‍⚕️"
    speaker_label = "Patient" if speaker == "patient" else "Clinician"

    html = f"""
    <div class="{turn_class}">
        <div class="speaker-label">{speaker_icon} {speaker_label} · Turn {turn_id}</div>
    """

    if spikes_stage and speaker == "clinician":
        spikes_color = get_label_color(spikes_stage, schema)
        html += f'<span class="annotation-badge" style="background-color: {spikes_color};">SPIKES: {spikes_stage.upper()}</span><br><br>'

    html += f'<div class="turn-text">{highlighted_text}</div>'

    # Show annotation badges
    if show_annotations and spans:
        html += '<div class="annotation-section">'
        for span in spans:
            label = span.get("label", "")
            color = get_label_color(label, schema)
            html += f'<span class="annotation-badge" style="background-color: {color}; color: #1a1a2e;">{format_label_name(label)}</span> '
        html += "</div>"

    html += "</div>"

    return html


# ============== Main Application ==============


def main():
    init_session_state()

    # Sidebar
    st.sidebar.title("🏥 BBN Annotation Tool")
    st.sidebar.markdown("---")

    # Load data
    schema = load_schema()
    conversations = load_conversations()

    # Conversation selector
    st.sidebar.subheader("📂 Conversations")
    if conversations:
        conv_options = {
            f"{c.get('id', 'Unknown')} - {c.get('metadata', {}).get('scenario', 'No scenario')}": i
            for i, c in enumerate(conversations)
        }
        selected_conv = st.sidebar.selectbox(
            "Select Conversation", options=list(conv_options.keys())
        )
        current_conv = conversations[conv_options[selected_conv]]

        # Load existing annotations when conversation changes
        if (
            "last_conv_id" not in st.session_state
            or st.session_state.last_conv_id != current_conv.get("id")
        ):
            load_existing_annotations(current_conv)
            st.session_state.last_conv_id = current_conv.get("id")
    else:
        st.sidebar.warning("No conversations found in data/samples/")
        current_conv = None

    # Agent configuration
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 AI Agent")

    agent_type = st.sidebar.selectbox(
        "Agent Type",
        ["react", "multi"],
        format_func=lambda x: "ReAct Agent" if x == "react" else "Multi-Agent",
    )

    provider = st.sidebar.selectbox("Provider", ["openai", "anthropic"])

    if provider == "openai":
        model = st.sidebar.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
    else:
        model = st.sidebar.selectbox("Model", ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"])

    st.session_state.agent_config = {
        "provider": provider,
        "model": model,
        "agent_type": agent_type,
        "api_key": os.getenv("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY", ""),
    }

    # Save button
    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Save Annotations", type="primary", use_container_width=True):
        if current_conv:
            merged_conv = merge_annotations_to_conversation(current_conv.copy())
            filepath = save_conversation(merged_conv, current_conv.get("filepath"))
            st.sidebar.success(f"Saved!")

    # Export button
    if current_conv:
        merged_conv = merge_annotations_to_conversation(current_conv.copy())
        st.sidebar.download_button(
            label="📤 Export JSON",
            data=json.dumps(merged_conv, indent=2, ensure_ascii=False),
            file_name=f"annotated_{current_conv.get('id', 'unknown')}.json",
            mime="application/json",
            use_container_width=True,
        )

    # ============== Main Content ==============
    # Title with show annotations toggle on the right
    title_col, toggle_col = st.columns([4, 1])
    with title_col:
        st.title("📖 Conversation Viewer")
    with toggle_col:
        st.markdown("<div style='height: 42px'></div>", unsafe_allow_html=True)  # Align with title
        show_annotations = st.toggle("Show Annotations", value=True)

    if current_conv:
        # Check if we need to reopen a dialog (after rerun)
        if st.session_state.open_dialog_turn_id is not None:
            open_turn_id = st.session_state.open_dialog_turn_id
            open_turn = next(
                (t for t in current_conv.get("turns", []) if t["turn_id"] == open_turn_id),
                None
            )
            if open_turn:
                annotation_dialog(open_turn, schema, current_conv)

        # Metadata header
        metadata = current_conv.get("metadata", {})
        st.info(
            f"**Scenario:** {metadata.get('scenario', 'N/A')} | "
            f"**Language:** {metadata.get('language', 'N/A')} | "
            f"**Date:** {metadata.get('date', 'N/A')}"
        )

        # Annotation stats
        total_spans = sum(
            len(st.session_state.current_annotations.get(t["turn_id"], {}).get("spans", []))
            for t in current_conv.get("turns", [])
        )
        st.caption(f"📊 Total annotations: {total_spans}")

        st.markdown("---")

        # Render each turn with annotate button
        for turn in current_conv.get("turns", []):
            # Render the turn card
            html = render_turn_card(turn, schema, show_annotations)
            st.markdown(html, unsafe_allow_html=True)

            # Annotate button below each turn
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button(f"✏️ Annotate", key=f"annotate_btn_{turn['turn_id']}", use_container_width=True):
                    st.session_state.open_dialog_turn_id = turn["turn_id"]
                    annotation_dialog(turn, schema, current_conv)
            with col2:
                # Show relation count if any
                turn_annotations = st.session_state.current_annotations.get(turn["turn_id"], {"relations": []})
                relations = turn_annotations.get("relations", [])
                if relations:
                    st.markdown(
                        f'<div class="relations-badge">🔗 {len(relations)} relation{"s" if len(relations) > 1 else ""}</div>',
                        unsafe_allow_html=True
                    )
    else:
        st.warning("No conversation selected or available.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("AI-Assisted Clinical Annotation")


if __name__ == "__main__":
    main()
