"""Manual annotation panel component."""

import streamlit as st
from utils import get_label_color, format_label_name
from utils.colors import get_labels_for_speaker, get_all_labels_flat
from services import add_span_annotation, set_spikes_stage
from config import SPIKES_STAGES


def render_manual_panel(turn, turn_id, speaker, text):
    """Render the manual annotation panel."""
    st.markdown("#### Manual Annotation")

    # Text selection input
    selected_text = st.text_input(
        "Text to annotate:",
        key=f"modal_text_{turn_id}",
        placeholder="Paste selected text here...",
    )

    if selected_text:
        if selected_text in text:
            start_idx = text.find(selected_text)
            st.success(f"Found at position {start_idx}")

            # Label selection
            st.markdown("**Choose label:**")
            label_groups = get_labels_for_speaker(speaker)

            # Create flat list for selectbox
            all_labels = get_all_labels_flat(speaker)

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

            if st.button("Add Annotation", type="primary", key=f"modal_add_{turn_id}"):
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
                    st.warning("This annotation already exists!")
        else:
            st.error("Text not found in this turn")

    # SPIKES stage for clinician
    if speaker == "clinician":
        st.markdown("---")
        st.markdown("**SPIKES Stage:**")
        spikes_options = ["None"] + SPIKES_STAGES
        current_spikes = st.session_state.current_annotations.get(turn_id, {}).get(
            "spikes_stage"
        )

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
