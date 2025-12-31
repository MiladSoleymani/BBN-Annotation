"""Relations panel component."""

import streamlit as st
from utils import format_label_name
from services import add_relation


def render_relations_panel(turn_id, conversation, turn_annotations):
    """Render the relations panel."""
    st.markdown("#### Link Relations")

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
                "display": f"T{t_id}: \"{span['text'][:25]}...\" [{format_label_name(span['label'])}]",
            }
            if t_speaker == "patient":
                all_patient_spans.append(span_info)
            else:
                all_clinician_spans.append(span_info)

    if all_patient_spans and all_clinician_spans:
        rel_col1, rel_col2 = st.columns(2)
        with rel_col1:
            from_options = ["Select patient EO..."] + [s["display"] for s in all_patient_spans]
            selected_from = st.selectbox(
                "From (Patient EO):", from_options, key=f"rel_from_{turn_id}"
            )
        with rel_col2:
            to_options = ["Select clinician response..."] + [
                s["display"] for s in all_clinician_spans
            ]
            selected_to = st.selectbox(
                "To (Clinician):", to_options, key=f"rel_to_{turn_id}"
            )

        if selected_from != "Select patient EO..." and selected_to != "Select clinician response...":
            if st.button("Create Link", key=f"create_rel_{turn_id}"):
                from_span = next(s for s in all_patient_spans if s["display"] == selected_from)
                to_span = next(s for s in all_clinician_spans if s["display"] == selected_to)
                add_relation(
                    to_span["turn_id"],
                    to_span["span_id"],
                    from_span["turn_id"],
                    from_span["span_id"],
                    "response_to",
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
                f'<span style="color:#16a34a;">Clinician: {from_text}</span>'
                f'<span class="rel-arrow"> -> </span>'
                f'<span class="rel-type">{rel["type"].replace("_", " ")}</span>'
                f'<span class="rel-arrow"> -> </span>'
                f'<span style="color:#7c3aed;">Patient: {to_text}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
