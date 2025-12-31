"""Turn card rendering component."""

import streamlit as st
from utils import get_label_color, format_label_name


def render_turn_card(turn, schema, show_annotations=True):
    """Render a conversation turn card. Returns HTML string."""
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

    spikes_stage = session_annotations.get("spikes_stage") or original_annotations.get(
        "spikes_stage"
    )

    # Build highlighted text using position-based insertion
    highlighted_text = text
    if show_annotations and spans:
        # Sort by start position in reverse to avoid index shifting
        sorted_spans = sorted(spans, key=lambda x: x.get("start", 0), reverse=True)
        for span in sorted_spans:
            label = span.get("label", "")
            color = get_label_color(label)
            start = span.get("start", 0)
            end = span.get("end", len(text))

            # Validate positions
            if 0 <= start < end <= len(highlighted_text):
                span_text = highlighted_text[start:end]
                highlighted_text = (
                    highlighted_text[:start]
                    + f'<span class="highlight-span" style="background-color: {color};" title="{format_label_name(label)}">{span_text}</span>'
                    + highlighted_text[end:]
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
        spikes_color = get_label_color(spikes_stage)
        html += f'<span class="annotation-badge" style="background-color: {spikes_color};">SPIKES: {spikes_stage.upper()}</span><br><br>'

    html += f'<div class="turn-text">{highlighted_text}</div>'

    # Show annotation badges
    if show_annotations and spans:
        html += '<div class="annotation-section">'
        for span in spans:
            label = span.get("label", "")
            color = get_label_color(label)
            html += f'<span class="annotation-badge" style="background-color: {color}; color: #1a1a2e;">{format_label_name(label)}</span> '
        html += "</div>"

    html += "</div>"

    return html
