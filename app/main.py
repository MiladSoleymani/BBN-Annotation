import streamlit as st
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
from datetime import datetime
import uuid

# Page configuration
st.set_page_config(
    page_title="BBN Annotation Tool",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling - works in both light and dark modes
st.markdown("""
<style>
    /* Turn cards */
    .patient-turn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        margin: 15px 0;
        border-left: 5px solid #5a4fcf;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        color: #ffffff !important;
    }
    .clinician-turn {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 20px;
        border-radius: 12px;
        margin: 15px 0;
        border-left: 5px solid #0d7d74;
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
        color: #ffffff !important;
    }
    .patient-turn *, .clinician-turn * {
        color: #ffffff !important;
    }
    .speaker-label {
        font-weight: 700;
        font-size: 1em;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.9;
    }
    .turn-text {
        font-size: 1.1em;
        line-height: 1.7;
        color: #ffffff !important;
    }
    .annotation-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        margin: 3px;
        color: #1a1a2e !important;
        font-weight: 600;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .highlight-span {
        padding: 3px 6px;
        border-radius: 5px;
        margin: 0 2px;
        font-weight: 600;
        color: #1a1a2e !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .annotation-section {
        margin-top: 15px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.3);
        font-size: 0.9em;
    }

    /* Annotation mode specific styles */
    .selectable-text {
        background: #1a1a2e;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        color: #ffffff;
        font-size: 1.1em;
        line-height: 1.8;
        cursor: text;
        user-select: text;
    }
    .annotation-card {
        background: linear-gradient(135deg, #2d3436 0%, #000000 100%);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #6c5ce7;
    }
    .span-item {
        background: rgba(255,255,255,0.1);
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 3px solid #00cec9;
    }
    .ai-suggestion {
        background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        color: #1a1a2e !important;
    }
    .ai-suggestion * {
        color: #1a1a2e !important;
    }
    .relation-item {
        background: rgba(116, 185, 255, 0.2);
        padding: 8px 12px;
        border-radius: 6px;
        margin: 5px 0;
        border: 1px solid #74b9ff;
    }

    /* Button styles */
    .stButton > button {
        border-radius: 20px;
        padding: 5px 20px;
        font-weight: 600;
    }

    /* Make text areas more visible */
    .stTextArea textarea {
        background-color: #2d3436 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)


# ============== Data Loading Functions ==============

def load_schema():
    """Load annotation schema from JSON file."""
    schema_path = Path(__file__).parent.parent / "data" / "annotation_schema.json"
    if schema_path.exists():
        with open(schema_path, 'r') as f:
            return json.load(f)
    return None


def load_conversations():
    """Load all conversation files from the samples directory."""
    samples_dir = Path(__file__).parent.parent / "data" / "samples"
    conversations = []
    if samples_dir.exists():
        for file in sorted(samples_dir.glob("*.json")):
            with open(file, 'r') as f:
                conv = json.load(f)
                conv['filename'] = file.name
                conv['filepath'] = str(file)
                conversations.append(conv)
    return conversations


def save_conversation(conversation, filepath=None):
    """Save conversation with annotations to JSON file."""
    if filepath is None:
        samples_dir = Path(__file__).parent.parent / "data" / "samples"
        filepath = samples_dir / f"annotated_{conversation.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filepath, 'w') as f:
        json.dump(conversation, f, indent=2, ensure_ascii=False)

    return filepath


# ============== Color and Label Functions ==============

def get_label_color(label, schema=None):
    """Get color for a label from the schema."""
    color_map = {
        # Patient EOs - Warm colors for feelings, cool for others
        'explicit_feeling': '#FF6B6B',
        'implicit_feeling': '#FFA07A',
        'explicit_appreciation': '#20E3B2',
        'implicit_appreciation': '#7DFFCC',
        'explicit_judgement': '#74B9FF',
        'implicit_judgement': '#A8D8FF',
        # Clinician Elicitations
        'direct_elicitation_feeling': '#FFD93D',
        'indirect_elicitation_feeling': '#FFE66D',
        'direct_elicitation_appreciation': '#FFA94D',
        'indirect_elicitation_appreciation': '#FFBE76',
        'direct_elicitation_judgement': '#FF9FF3',
        'indirect_elicitation_judgement': '#FFB8E0',
        # Clinician Responses
        'acceptance_positive_regard_explicit_judgement': '#00D9A5',
        'acceptance_positive_regard_implicit_judgement': '#55EFC4',
        'acceptance_positive_regard_repetition': '#81ECEC',
        'acceptance_positive_regard_allowing': '#B8F5F1',
        'acceptance_neutral_support_appreciation': '#FDCB6E',
        'acceptance_neutral_support_judgement': '#FFE5A0',
        'sharing_feeling': '#E056FD',
        'sharing_appreciation': '#F0A1FF',
        'sharing_judgement': '#FFD1FF',
        'understanding_feeling': '#54A0FF',
        'understanding_appreciation': '#82CCFF',
        'understanding_judgement': '#B8E0FF',
        # SPIKES
        'setting': '#FF6B6B',
        'perception': '#FFA502',
        'invitation': '#FFD93D',
        'knowledge': '#2ED573',
        'empathy': '#54A0FF',
        'strategy': '#A55EEA',
    }
    return color_map.get(label, '#95A5A6')


def format_label_name(label):
    """Format label name for display."""
    return label.replace('_', ' ').title()


def get_label_options():
    """Get all available label options organized by category."""
    return {
        "Patient EOs": {
            "Feelings": ["explicit_feeling", "implicit_feeling"],
            "Appreciation": ["explicit_appreciation", "implicit_appreciation"],
            "Judgement": ["explicit_judgement", "implicit_judgement"]
        },
        "Clinician Elicitations": {
            "Feelings": ["direct_elicitation_feeling", "indirect_elicitation_feeling"],
            "Appreciation": ["direct_elicitation_appreciation", "indirect_elicitation_appreciation"],
            "Judgement": ["direct_elicitation_judgement", "indirect_elicitation_judgement"]
        },
        "Clinician Responses - Acceptance": {
            "Positive Regard": [
                "acceptance_positive_regard_explicit_judgement",
                "acceptance_positive_regard_implicit_judgement",
                "acceptance_positive_regard_repetition",
                "acceptance_positive_regard_allowing"
            ],
            "Neutral Support": [
                "acceptance_neutral_support_appreciation",
                "acceptance_neutral_support_judgement"
            ]
        },
        "Clinician Responses - Sharing": {
            "Types": ["sharing_feeling", "sharing_appreciation", "sharing_judgement"]
        },
        "Clinician Responses - Understanding": {
            "Types": ["understanding_feeling", "understanding_appreciation", "understanding_judgement"]
        },
        "SPIKES Stages": {
            "Stages": ["setting", "perception", "invitation", "knowledge", "empathy", "strategy"]
        }
    }


# ============== Session State Initialization ==============

def init_session_state():
    """Initialize session state variables."""
    if 'current_annotations' not in st.session_state:
        st.session_state.current_annotations = {}

    if 'selected_turn' not in st.session_state:
        st.session_state.selected_turn = None

    if 'selected_text' not in st.session_state:
        st.session_state.selected_text = ""

    if 'pending_spans' not in st.session_state:
        st.session_state.pending_spans = []

    if 'pending_relations' not in st.session_state:
        st.session_state.pending_relations = []

    if 'ai_suggestions' not in st.session_state:
        st.session_state.ai_suggestions = []

    if 'annotation_mode' not in st.session_state:
        st.session_state.annotation_mode = "view"


# ============== Annotation Functions ==============

def add_span_annotation(turn_id, text, start, end, label):
    """Add a span annotation to the current annotations."""
    if turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[turn_id] = {
            'spans': [],
            'relations': [],
            'spikes_stage': None
        }

    span = {
        'span_id': f"span_{uuid.uuid4().hex[:8]}",
        'text': text,
        'start': start,
        'end': end,
        'label': label
    }

    st.session_state.current_annotations[turn_id]['spans'].append(span)
    return span['span_id']


def remove_span_annotation(turn_id, span_id):
    """Remove a span annotation."""
    if turn_id in st.session_state.current_annotations:
        st.session_state.current_annotations[turn_id]['spans'] = [
            s for s in st.session_state.current_annotations[turn_id]['spans']
            if s['span_id'] != span_id
        ]
        # Also remove related relations
        st.session_state.current_annotations[turn_id]['relations'] = [
            r for r in st.session_state.current_annotations[turn_id]['relations']
            if r['from'] != span_id and r['to'] != span_id
        ]


def add_relation(from_turn_id, from_span_id, to_turn_id, to_span_id, relation_type):
    """Add a relation between two spans."""
    # Store relation in the 'from' turn
    if from_turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[from_turn_id] = {
            'spans': [],
            'relations': [],
            'spikes_stage': None
        }

    relation = {
        'relation_id': f"rel_{uuid.uuid4().hex[:8]}",
        'from': from_span_id,
        'to': to_span_id,
        'to_turn_id': to_turn_id,
        'type': relation_type
    }

    st.session_state.current_annotations[from_turn_id]['relations'].append(relation)
    return relation['relation_id']


def set_spikes_stage(turn_id, stage):
    """Set SPIKES stage for a clinician turn."""
    if turn_id not in st.session_state.current_annotations:
        st.session_state.current_annotations[turn_id] = {
            'spans': [],
            'relations': [],
            'spikes_stage': None
        }
    st.session_state.current_annotations[turn_id]['spikes_stage'] = stage


def merge_annotations_to_conversation(conversation):
    """Merge current session annotations into the conversation object."""
    for turn in conversation.get('turns', []):
        turn_id = turn['turn_id']
        if turn_id in st.session_state.current_annotations:
            if 'annotations' not in turn:
                turn['annotations'] = {'spans': [], 'relations': []}

            # Merge spans
            existing_span_ids = {s['span_id'] for s in turn['annotations'].get('spans', [])}
            for span in st.session_state.current_annotations[turn_id].get('spans', []):
                if span['span_id'] not in existing_span_ids:
                    turn['annotations']['spans'].append(span)

            # Merge relations
            existing_rel_ids = {r.get('relation_id') for r in turn['annotations'].get('relations', [])}
            for rel in st.session_state.current_annotations[turn_id].get('relations', []):
                if rel.get('relation_id') not in existing_rel_ids:
                    turn['annotations']['relations'].append(rel)

            # Set SPIKES stage
            if st.session_state.current_annotations[turn_id].get('spikes_stage'):
                turn['annotations']['spikes_stage'] = st.session_state.current_annotations[turn_id]['spikes_stage']

    return conversation


def load_existing_annotations(conversation):
    """Load existing annotations from conversation into session state."""
    st.session_state.current_annotations = {}

    for turn in conversation.get('turns', []):
        turn_id = turn['turn_id']
        annotations = turn.get('annotations', {})

        if annotations:
            st.session_state.current_annotations[turn_id] = {
                'spans': annotations.get('spans', []).copy(),
                'relations': annotations.get('relations', []).copy(),
                'spikes_stage': annotations.get('spikes_stage')
            }


# ============== Render Functions ==============

def render_turn_with_highlights(turn, schema, show_annotations=True):
    """Render a conversation turn with highlighted annotations."""
    text = turn['text']
    speaker = turn['speaker']
    turn_id = turn['turn_id']

    # Get annotations from both original and session state
    original_annotations = turn.get('annotations', {})
    session_annotations = st.session_state.current_annotations.get(turn_id, {})

    # Combine spans
    spans = original_annotations.get('spans', []).copy()
    for span in session_annotations.get('spans', []):
        if span['span_id'] not in [s['span_id'] for s in spans]:
            spans.append(span)

    spikes_stage = session_annotations.get('spikes_stage') or original_annotations.get('spikes_stage')

    # Sort spans by start position (reverse for proper replacement)
    sorted_spans = sorted(spans, key=lambda x: x.get('start', 0), reverse=True)

    highlighted_text = text
    if show_annotations and spans:
        for span in sorted_spans:
            label = span.get('label', '')
            color = get_label_color(label, schema)
            span_text = span.get('text', '')
            if span_text in highlighted_text:
                highlighted_text = highlighted_text.replace(
                    span_text,
                    f'<span class="highlight-span" style="background-color: {color}; color: #1a1a2e !important;" title="{format_label_name(label)}">{span_text}</span>',
                    1
                )

    # Build the turn HTML
    turn_class = "patient-turn" if speaker == "patient" else "clinician-turn"
    speaker_icon = "🧑‍🦱" if speaker == "patient" else "👨‍⚕️"
    speaker_label = "Patient" if speaker == "patient" else "Clinician"

    html = f'''
    <div class="{turn_class}">
        <div class="speaker-label">{speaker_icon} {speaker_label} (Turn {turn_id})</div>
    '''

    if spikes_stage and speaker == "clinician":
        spikes_color = get_label_color(spikes_stage, schema)
        html += f'<span class="annotation-badge" style="background-color: {spikes_color}; color: #1a1a2e;">SPIKES: {spikes_stage.upper()}</span><br><br>'

    html += f'<div class="turn-text">{highlighted_text}</div>'

    # Show annotation details
    if show_annotations and spans:
        html += '<div class="annotation-section">'
        html += '<strong>Annotations:</strong><br>'
        for span in spans:
            label = span.get('label', '')
            color = get_label_color(label, schema)
            html += f'<span class="annotation-badge" style="background-color: {color}; color: #1a1a2e;">{format_label_name(label)}</span> '
        html += '</div>'

    html += '</div>'
    return html


def render_annotation_interface(turn, schema):
    """Render the annotation interface for a single turn."""
    turn_id = turn['turn_id']
    speaker = turn['speaker']
    text = turn['text']

    st.markdown(f"### Turn {turn_id} - {speaker.title()}")

    # Display the text
    st.markdown(f'<div class="selectable-text">{text}</div>', unsafe_allow_html=True)

    # Text selection input
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_text = st.text_input(
            "Selected text to annotate:",
            key=f"text_input_{turn_id}",
            placeholder="Copy and paste the text you want to annotate here..."
        )

    with col2:
        if selected_text and selected_text in text:
            start_idx = text.find(selected_text)
            st.success(f"Found at position {start_idx}")
        elif selected_text:
            st.error("Text not found in turn")

    # Label selection
    if selected_text and selected_text in text:
        st.markdown("**Select Label:**")

        label_options = get_label_options()

        # Filter labels based on speaker
        if speaker == "patient":
            relevant_categories = ["Patient EOs"]
        else:
            relevant_categories = [
                "Clinician Elicitations",
                "Clinician Responses - Acceptance",
                "Clinician Responses - Sharing",
                "Clinician Responses - Understanding"
            ]

        # Create tabs for categories
        tabs = st.tabs(relevant_categories)

        for tab, category in zip(tabs, relevant_categories):
            with tab:
                subcategories = label_options.get(category, {})
                for subcat, labels in subcategories.items():
                    st.markdown(f"**{subcat}:**")
                    cols = st.columns(len(labels))
                    for col, label in zip(cols, labels):
                        with col:
                            color = get_label_color(label)
                            if st.button(
                                format_label_name(label),
                                key=f"btn_{turn_id}_{label}_{selected_text[:10]}",
                                help=f"Apply {format_label_name(label)}"
                            ):
                                start_idx = text.find(selected_text)
                                add_span_annotation(
                                    turn_id,
                                    selected_text,
                                    start_idx,
                                    start_idx + len(selected_text),
                                    label
                                )
                                st.success(f"Added: {format_label_name(label)}")
                                st.rerun()

    # SPIKES stage for clinician turns
    if speaker == "clinician":
        st.markdown("---")
        st.markdown("**SPIKES Stage:**")
        spikes_options = ["None", "setting", "perception", "invitation", "knowledge", "empathy", "strategy"]
        current_spikes = st.session_state.current_annotations.get(turn_id, {}).get('spikes_stage')

        selected_spikes = st.selectbox(
            "Select SPIKES stage:",
            spikes_options,
            index=spikes_options.index(current_spikes) if current_spikes in spikes_options else 0,
            key=f"spikes_{turn_id}"
        )

        if selected_spikes != "None" and selected_spikes != current_spikes:
            set_spikes_stage(turn_id, selected_spikes)
            st.rerun()

    # Display current annotations for this turn
    st.markdown("---")
    st.markdown("**Current Annotations:**")

    turn_annotations = st.session_state.current_annotations.get(turn_id, {'spans': [], 'relations': []})

    if turn_annotations.get('spans'):
        for span in turn_annotations['spans']:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                color = get_label_color(span['label'])
                st.markdown(f'<span style="background-color: {color}; color: #1a1a2e; padding: 2px 8px; border-radius: 4px;">"{span["text"]}"</span>', unsafe_allow_html=True)
            with col2:
                st.caption(format_label_name(span['label']))
            with col3:
                if st.button("🗑️", key=f"del_{span['span_id']}", help="Remove annotation"):
                    remove_span_annotation(turn_id, span['span_id'])
                    st.rerun()
    else:
        st.caption("No annotations yet")


def render_relation_editor(conversation):
    """Render the relation editor interface."""
    st.markdown("### Relation Editor")
    st.markdown("Connect Empathic Opportunities to Clinician Responses")

    # Collect all spans from all turns
    all_spans = []
    for turn in conversation.get('turns', []):
        turn_id = turn['turn_id']
        speaker = turn['speaker']
        turn_annotations = st.session_state.current_annotations.get(turn_id, {'spans': []})

        for span in turn_annotations.get('spans', []):
            all_spans.append({
                'turn_id': turn_id,
                'speaker': speaker,
                'span_id': span['span_id'],
                'text': span['text'][:50] + "..." if len(span['text']) > 50 else span['text'],
                'label': span['label'],
                'display': f"T{turn_id} ({speaker}): {span['text'][:30]}... [{format_label_name(span['label'])}]"
            })

    if len(all_spans) < 2:
        st.info("Add at least 2 span annotations to create relations.")
        return

    # Patient spans (EOs)
    patient_spans = [s for s in all_spans if s['speaker'] == 'patient']
    # Clinician spans (responses/elicitations)
    clinician_spans = [s for s in all_spans if s['speaker'] == 'clinician']

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**From (Patient EO):**")
        from_options = {s['display']: s for s in patient_spans}
        selected_from = st.selectbox(
            "Select source span:",
            options=["Select..."] + list(from_options.keys()),
            key="relation_from"
        )

    with col2:
        st.markdown("**To (Clinician Response):**")
        to_options = {s['display']: s for s in clinician_spans}
        selected_to = st.selectbox(
            "Select target span:",
            options=["Select..."] + list(to_options.keys()),
            key="relation_to"
        )

    relation_type = st.selectbox(
        "Relation type:",
        ["response_to", "elicitation_of"],
        key="relation_type"
    )

    if st.button("Add Relation", type="primary"):
        if selected_from != "Select..." and selected_to != "Select...":
            from_span = from_options[selected_from]
            to_span = to_options[selected_to]

            add_relation(
                to_span['turn_id'],  # Store in clinician turn
                to_span['span_id'],
                from_span['turn_id'],
                from_span['span_id'],
                relation_type
            )
            st.success("Relation added!")
            st.rerun()
        else:
            st.error("Please select both source and target spans")

    # Display existing relations
    st.markdown("---")
    st.markdown("**Existing Relations:**")

    has_relations = False
    for turn in conversation.get('turns', []):
        turn_id = turn['turn_id']
        turn_annotations = st.session_state.current_annotations.get(turn_id, {'relations': []})

        for rel in turn_annotations.get('relations', []):
            has_relations = True
            st.markdown(f'<div class="relation-item">**{rel["from"]}** → _{rel["type"]}_ → **{rel["to"]}**</div>', unsafe_allow_html=True)

    if not has_relations:
        st.caption("No relations yet")


def render_ai_suggestion_panel(turn, schema):
    """Render AI suggestion panel (placeholder for future AI integration)."""
    st.markdown("### 🤖 AI Suggestions")

    st.info("AI suggestions will appear here. Click 'Generate AI Suggestions' to get automated annotation proposals.")

    if st.button("🔮 Generate AI Suggestions", type="primary", key=f"ai_btn_{turn['turn_id']}"):
        # Placeholder - this is where AI integration will go
        st.session_state.ai_suggestions = [
            {
                'turn_id': turn['turn_id'],
                'text': turn['text'][:50] + "..." if len(turn['text']) > 50 else turn['text'],
                'suggested_label': 'implicit_feeling',
                'confidence': 0.85,
                'reasoning': 'The patient expresses concern indirectly through their statement.'
            }
        ]
        st.rerun()

    # Display AI suggestions
    if st.session_state.ai_suggestions:
        for suggestion in st.session_state.ai_suggestions:
            if suggestion['turn_id'] == turn['turn_id']:
                st.markdown(f'''
                <div class="ai-suggestion">
                    <strong>Suggested:</strong> {format_label_name(suggestion['suggested_label'])}<br>
                    <strong>Text:</strong> "{suggestion['text']}"<br>
                    <strong>Confidence:</strong> {suggestion['confidence']*100:.0f}%<br>
                    <strong>Reasoning:</strong> {suggestion['reasoning']}
                </div>
                ''', unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✅ Accept", key=f"accept_{suggestion['turn_id']}"):
                        add_span_annotation(
                            suggestion['turn_id'],
                            suggestion['text'],
                            0,
                            len(suggestion['text']),
                            suggestion['suggested_label']
                        )
                        st.session_state.ai_suggestions = []
                        st.rerun()
                with col2:
                    if st.button("✏️ Modify", key=f"modify_{suggestion['turn_id']}"):
                        st.session_state.selected_text = suggestion['text']
                with col3:
                    if st.button("❌ Reject", key=f"reject_{suggestion['turn_id']}"):
                        st.session_state.ai_suggestions = []
                        st.rerun()


def render_statistics(conversation):
    """Render statistics dashboard."""
    stats = compute_statistics(conversation)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Turns", stats['total_turns'])
    with col2:
        st.metric("Patient Turns", stats['patient_turns'])
    with col3:
        st.metric("Clinician Turns", stats['clinician_turns'])
    with col4:
        st.metric("Annotations", stats['total_spans'])

    # EO Distribution Chart
    if stats['eo_counts']:
        st.subheader("Empathic Opportunities Distribution")
        eo_data = [(format_label_name(k), v) for k, v in stats['eo_counts'].items()]
        if eo_data:
            labels, values = zip(*eo_data)
            fig = px.bar(
                x=list(labels),
                y=list(values),
                color=list(labels),
                title="Patient Empathic Opportunities"
            )
            fig.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)


def compute_statistics(conversation):
    """Compute statistics for a conversation."""
    stats = {
        'total_turns': len(conversation.get('turns', [])),
        'patient_turns': 0,
        'clinician_turns': 0,
        'eo_counts': defaultdict(int),
        'total_spans': 0,
        'total_relations': 0
    }

    for turn in conversation.get('turns', []):
        if turn['speaker'] == 'patient':
            stats['patient_turns'] += 1
        else:
            stats['clinician_turns'] += 1

        # Count from session state annotations
        turn_id = turn['turn_id']
        turn_annotations = st.session_state.current_annotations.get(turn_id, {'spans': [], 'relations': []})

        for span in turn_annotations.get('spans', []):
            stats['total_spans'] += 1
            label = span.get('label', '')
            if turn['speaker'] == 'patient':
                stats['eo_counts'][label] += 1

        stats['total_relations'] += len(turn_annotations.get('relations', []))

    return stats


# ============== Main Application ==============

def main():
    init_session_state()

    # Sidebar
    st.sidebar.title("🏥 BBN Annotation Tool")
    st.sidebar.markdown("---")

    # Load data
    schema = load_schema()
    conversations = load_conversations()

    # Mode selection
    st.sidebar.subheader("Mode")
    mode = st.sidebar.radio(
        "Select mode:",
        ["📖 View", "✏️ Annotate", "🔗 Relations", "📊 Statistics"],
        key="mode_selector"
    )

    st.sidebar.markdown("---")

    # Conversation selector
    if conversations:
        conv_options = {
            f"{c.get('id', 'Unknown')} - {c.get('metadata', {}).get('scenario', 'No scenario')}": i
            for i, c in enumerate(conversations)
        }
        selected_conv = st.sidebar.selectbox(
            "Select Conversation",
            options=list(conv_options.keys())
        )
        current_conv = conversations[conv_options[selected_conv]]

        # Load existing annotations when conversation changes
        if 'last_conv_id' not in st.session_state or st.session_state.last_conv_id != current_conv.get('id'):
            load_existing_annotations(current_conv)
            st.session_state.last_conv_id = current_conv.get('id')
    else:
        st.sidebar.warning("No conversations found in data/samples/")
        current_conv = None

    # Display options
    st.sidebar.markdown("---")
    st.sidebar.subheader("Display Options")
    show_annotations = st.sidebar.checkbox("Show Annotations", value=True)

    # Save button
    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Save Annotations", type="primary"):
        if current_conv:
            merged_conv = merge_annotations_to_conversation(current_conv.copy())
            filepath = save_conversation(merged_conv, current_conv.get('filepath'))
            st.sidebar.success(f"Saved to {filepath}")

    # Export button
    if st.sidebar.button("📤 Export as JSON"):
        if current_conv:
            merged_conv = merge_annotations_to_conversation(current_conv.copy())
            st.sidebar.download_button(
                label="Download JSON",
                data=json.dumps(merged_conv, indent=2, ensure_ascii=False),
                file_name=f"annotated_{current_conv.get('id', 'unknown')}.json",
                mime="application/json"
            )

    # Main content
    if mode == "📖 View":
        st.title("📖 Conversation Viewer")

        if current_conv:
            metadata = current_conv.get('metadata', {})
            st.info(f"**Scenario:** {metadata.get('scenario', 'N/A')} | **Language:** {metadata.get('language', 'N/A')} | **Date:** {metadata.get('date', 'N/A')}")

            for turn in current_conv.get('turns', []):
                html = render_turn_with_highlights(turn, schema, show_annotations)
                st.markdown(html, unsafe_allow_html=True)

                # Show relations
                if show_annotations:
                    turn_id = turn['turn_id']
                    turn_annotations = st.session_state.current_annotations.get(turn_id, {'relations': []})
                    relations = turn_annotations.get('relations', [])
                    if relations:
                        with st.expander("View Relations"):
                            for rel in relations:
                                st.write(f"**{rel['from']}** → _{rel['type']}_ → **{rel['to']}**")
        else:
            st.warning("No conversation selected or available.")

    elif mode == "✏️ Annotate":
        st.title("✏️ Annotation Mode")

        if current_conv:
            metadata = current_conv.get('metadata', {})
            st.info(f"**Scenario:** {metadata.get('scenario', 'N/A')}")

            # Turn selector
            turn_options = {
                f"Turn {t['turn_id']} ({t['speaker'].title()}): {t['text'][:50]}...": t['turn_id']
                for t in current_conv.get('turns', [])
            }

            selected_turn_display = st.selectbox(
                "Select turn to annotate:",
                options=list(turn_options.keys())
            )

            selected_turn_id = turn_options[selected_turn_display]
            selected_turn = next(t for t in current_conv['turns'] if t['turn_id'] == selected_turn_id)

            col1, col2 = st.columns([2, 1])

            with col1:
                render_annotation_interface(selected_turn, schema)

            with col2:
                render_ai_suggestion_panel(selected_turn, schema)
        else:
            st.warning("No conversation selected.")

    elif mode == "🔗 Relations":
        st.title("🔗 Relation Editor")

        if current_conv:
            render_relation_editor(current_conv)
        else:
            st.warning("No conversation selected.")

    elif mode == "📊 Statistics":
        st.title("📊 Statistics Dashboard")

        if current_conv:
            render_statistics(current_conv)
        else:
            st.warning("No conversation selected.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("BBN Annotation Tool v2.0")
    st.sidebar.caption("AI-Assisted Annotation")


if __name__ == "__main__":
    main()
