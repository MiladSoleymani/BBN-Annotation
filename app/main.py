import streamlit as st
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict

# Page configuration
st.set_page_config(
    page_title="BBN Annotation Viewer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling - works in both light and dark modes
st.markdown("""
<style>
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
    .spikes-badge {
        background-color: #ffd93d !important;
        color: #1a1a2e !important;
    }
    .stats-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
    .annotation-section strong {
        opacity: 0.85;
    }
</style>
""", unsafe_allow_html=True)


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
        for file in samples_dir.glob("*.json"):
            with open(file, 'r') as f:
                conv = json.load(f)
                conv['filename'] = file.name
                conversations.append(conv)
    return conversations


def get_label_color(label, schema):
    """Get color for a label from the schema."""
    color_map = {
        # Patient EOs - Warm colors for feelings, cool for others
        'explicit_feeling': '#FF6B6B',      # Coral red
        'implicit_feeling': '#FFA07A',      # Light salmon
        'explicit_appreciation': '#20E3B2',  # Mint green
        'implicit_appreciation': '#7DFFCC',  # Light mint
        'explicit_judgement': '#74B9FF',     # Sky blue
        'implicit_judgement': '#A8D8FF',     # Light sky blue
        # Clinician Elicitations - Yellows/Oranges
        'direct_elicitation_feeling': '#FFD93D',      # Bright yellow
        'indirect_elicitation_feeling': '#FFE66D',    # Light yellow
        'direct_elicitation_appreciation': '#FFA94D', # Orange
        'indirect_elicitation_appreciation': '#FFBE76', # Light orange
        'direct_elicitation_judgement': '#FF9FF3',    # Pink
        'indirect_elicitation_judgement': '#FFB8E0',  # Light pink
        # Clinician Responses - Greens/Teals
        'acceptance_positive_regard_explicit_judgement': '#00D9A5',  # Teal
        'acceptance_positive_regard_implicit_judgement': '#55EFC4',  # Light teal
        'acceptance_positive_regard_repetition': '#81ECEC',          # Cyan
        'acceptance_positive_regard_allowing': '#B8F5F1',            # Light cyan
        'acceptance_neutral_support_appreciation': '#FDCB6E',        # Golden
        'acceptance_neutral_support_judgement': '#FFE5A0',           # Light golden
        'sharing_feeling': '#E056FD',       # Magenta
        'sharing_appreciation': '#F0A1FF',  # Light magenta
        'sharing_judgement': '#FFD1FF',     # Very light magenta
        'understanding_feeling': '#54A0FF', # Blue
        'understanding_appreciation': '#82CCFF', # Light blue
        'understanding_judgement': '#B8E0FF',    # Very light blue
        # SPIKES - Distinct vibrant colors
        'setting': '#FF6B6B',      # Red
        'perception': '#FFA502',   # Orange
        'invitation': '#FFD93D',   # Yellow
        'knowledge': '#2ED573',    # Green
        'empathy': '#54A0FF',      # Blue
        'strategy': '#A55EEA',     # Purple
    }
    return color_map.get(label, '#95A5A6')


def format_label_name(label):
    """Format label name for display."""
    return label.replace('_', ' ').title()


def render_turn_with_highlights(turn, schema, show_annotations=True):
    """Render a conversation turn with highlighted annotations."""
    text = turn['text']
    speaker = turn['speaker']
    annotations = turn.get('annotations', {})
    spans = annotations.get('spans', [])
    spikes_stage = annotations.get('spikes_stage', None)

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
        <div class="speaker-label">{speaker_icon} {speaker_label}</div>
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


def compute_statistics(conversation):
    """Compute statistics for a conversation."""
    stats = {
        'total_turns': len(conversation.get('turns', [])),
        'patient_turns': 0,
        'clinician_turns': 0,
        'eo_counts': defaultdict(int),
        'elicitation_counts': defaultdict(int),
        'response_counts': defaultdict(int),
        'spikes_stages': defaultdict(int),
        'total_relations': 0
    }

    for turn in conversation.get('turns', []):
        if turn['speaker'] == 'patient':
            stats['patient_turns'] += 1
        else:
            stats['clinician_turns'] += 1

        annotations = turn.get('annotations', {})

        # Count SPIKES stages
        if 'spikes_stage' in annotations:
            stats['spikes_stages'][annotations['spikes_stage']] += 1

        # Count spans
        for span in annotations.get('spans', []):
            label = span.get('label', '')
            if 'feeling' in label or 'appreciation' in label or 'judgement' in label:
                if turn['speaker'] == 'patient':
                    stats['eo_counts'][label] += 1
                elif 'elicitation' in label:
                    stats['elicitation_counts'][label] += 1
                else:
                    stats['response_counts'][label] += 1

        # Count relations
        stats['total_relations'] += len(annotations.get('relations', []))

    return stats


def render_statistics(stats):
    """Render statistics dashboard."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Turns", stats['total_turns'])
    with col2:
        st.metric("Patient Turns", stats['patient_turns'])
    with col3:
        st.metric("Clinician Turns", stats['clinician_turns'])
    with col4:
        st.metric("Relations", stats['total_relations'])

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

    # SPIKES Stages Distribution
    if stats['spikes_stages']:
        st.subheader("SPIKES Stages Distribution")
        spikes_data = [(k.upper(), v) for k, v in stats['spikes_stages'].items()]
        labels, values = zip(*spikes_data)
        fig = px.pie(
            names=list(labels),
            values=list(values),
            title="SPIKES Protocol Stages"
        )
        st.plotly_chart(fig, use_container_width=True)


def render_schema_reference(schema):
    """Render the annotation schema reference."""
    st.subheader("Patient: Empathic Opportunities (EOs)")

    # Create tabs for different categories
    tab1, tab2, tab3 = st.tabs(["Feelings", "Appreciation", "Judgement"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Explicit Feelings**")
            st.markdown(f'<span style="background-color: #FF6B6B40; padding: 5px 10px; border-radius: 5px;">Direct expression of emotion</span>', unsafe_allow_html=True)
            st.caption("Examples: 'I'm sad', 'I cried', 'I'm in pain'")
        with col2:
            st.markdown("**Implicit Feelings**")
            st.markdown(f'<span style="background-color: #FF8E8E40; padding: 5px 10px; border-radius: 5px;">Indirect expression via experiences</span>', unsafe_allow_html=True)
            st.caption("Examples: 'My aunt had the same condition...'")

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Explicit Appreciation**")
            st.markdown(f'<span style="background-color: #4ECDC440; padding: 5px 10px; border-radius: 5px;">Direct attitude toward things/events</span>', unsafe_allow_html=True)
            st.caption("Examples: 'The MRI was boring'")
        with col2:
            st.markdown("**Implicit Appreciation**")
            st.markdown(f'<span style="background-color: #7ED8D340; padding: 5px 10px; border-radius: 5px;">Indirect attitude toward things/events</span>', unsafe_allow_html=True)
            st.caption("Examples: 'My symptoms don't seem to improve...'")

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Explicit Judgement**")
            st.markdown(f'<span style="background-color: #45B7D140; padding: 5px 10px; border-radius: 5px;">Direct attitude toward self/others</span>', unsafe_allow_html=True)
            st.caption("Examples: 'The nurses weren't helpful'")
        with col2:
            st.markdown("**Implicit Judgement**")
            st.markdown(f'<span style="background-color: #73C8DF40; padding: 5px 10px; border-radius: 5px;">Indirect attitude toward self/others</span>', unsafe_allow_html=True)
            st.caption("Examples: 'I'm not very consistent...'")

    st.divider()

    st.subheader("Clinician: Empathic Responses")

    resp_tab1, resp_tab2, resp_tab3, resp_tab4 = st.tabs(["Acceptance", "Sharing", "Understanding", "Elicitations"])

    with resp_tab1:
        st.markdown("**Unconditional Positive Regard**")
        st.caption("Positive judgements, repetition, allowing full expression")
        st.markdown("**Neutral Support**")
        st.caption("Normalizing feelings, denying negative self-assessment")

    with resp_tab2:
        st.caption("Sharing patient's feelings/views through expressed agreement")
        st.caption("Examples: 'I would also feel anxious in this situation'")

    with resp_tab3:
        st.caption("Understanding and acknowledgement of patient's views/feelings")
        st.caption("Examples: 'I understand you're worried about...'")

    with resp_tab4:
        st.caption("Direct/Indirect elicitations of feelings, appreciation, judgement")
        st.caption("Examples: 'How do you feel about that?'")

    st.divider()

    st.subheader("SPIKES Protocol Stages")
    spikes_cols = st.columns(6)
    stages = [
        ("S", "Setting", "#E74C3C"),
        ("P", "Perception", "#E67E22"),
        ("I", "Invitation", "#F1C40F"),
        ("K", "Knowledge", "#27AE60"),
        ("E", "Empathy", "#3498DB"),
        ("S", "Strategy", "#9B59B6")
    ]
    for col, (letter, name, color) in zip(spikes_cols, stages):
        with col:
            st.markdown(f'<div style="text-align: center; background-color: {color}20; padding: 10px; border-radius: 10px; border: 2px solid {color};"><strong style="color: {color};">{letter}</strong><br><small>{name}</small></div>', unsafe_allow_html=True)


def main():
    # Sidebar
    st.sidebar.title("🏥 BBN Annotation")
    st.sidebar.markdown("---")

    # Load data
    schema = load_schema()
    conversations = load_conversations()

    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Conversation Viewer", "Annotation Schema", "Statistics"],
        index=0
    )

    st.sidebar.markdown("---")

    # Conversation selector
    if conversations:
        conv_options = {f"{c.get('id', 'Unknown')} - {c.get('metadata', {}).get('scenario', 'No scenario')}": i
                       for i, c in enumerate(conversations)}
        selected_conv = st.sidebar.selectbox(
            "Select Conversation",
            options=list(conv_options.keys())
        )
        current_conv = conversations[conv_options[selected_conv]]
    else:
        st.sidebar.warning("No conversations found in data/samples/")
        current_conv = None

    # Display options
    st.sidebar.markdown("---")
    st.sidebar.subheader("Display Options")
    show_annotations = st.sidebar.checkbox("Show Annotations", value=True)
    show_relations = st.sidebar.checkbox("Show Relations", value=True)

    # Main content
    if page == "Conversation Viewer":
        st.title("📋 Conversation Viewer")

        if current_conv:
            # Conversation metadata
            metadata = current_conv.get('metadata', {})
            st.info(f"**Scenario:** {metadata.get('scenario', 'N/A')} | **Language:** {metadata.get('language', 'N/A')} | **Date:** {metadata.get('date', 'N/A')}")

            # Render turns
            for turn in current_conv.get('turns', []):
                html = render_turn_with_highlights(turn, schema, show_annotations)
                st.markdown(html, unsafe_allow_html=True)

                # Show relations
                if show_relations and show_annotations:
                    relations = turn.get('annotations', {}).get('relations', [])
                    if relations:
                        with st.expander("View Relations"):
                            for rel in relations:
                                st.write(f"**{rel['from']}** → _{rel['type']}_ → **{rel['to']}**")
        else:
            st.warning("No conversation selected or available.")

    elif page == "Annotation Schema":
        st.title("📚 Annotation Schema Reference")
        st.markdown("Reference guide for the BBN Empathy annotation framework.")
        st.divider()

        if schema:
            render_schema_reference(schema)
        else:
            st.error("Schema file not found.")

    elif page == "Statistics":
        st.title("📊 Statistics Dashboard")

        if current_conv:
            stats = compute_statistics(current_conv)
            render_statistics(stats)
        else:
            st.warning("No conversation selected.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("BBN Annotation Tool v1.0")
    st.sidebar.caption("Based on Appraisal Framework for Clinical Empathy")


if __name__ == "__main__":
    main()
