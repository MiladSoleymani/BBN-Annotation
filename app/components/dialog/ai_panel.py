"""AI suggestions panel component."""

import os
import streamlit as st
from utils import get_label_color, format_label_name
from services import run_agent_on_turn, agent_result_to_suggestions, add_span_annotation


def render_ai_panel(turn, turn_id, conversation):
    """Render the AI suggestions panel."""
    st.markdown("#### AI Suggestions")

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

        if st.button("Generate Suggestions", key=f"modal_ai_{turn_id}"):
            with st.spinner("Analyzing..."):
                result = run_agent_on_turn(turn, context)
                if result:
                    st.session_state.ai_suggestions = agent_result_to_suggestions(
                        result, turn_id
                    )
                    st.rerun()

    # Display suggestions
    suggestions_for_turn = [
        s for s in st.session_state.ai_suggestions if s["turn_id"] == turn_id
    ]

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
                if st.button("Accept", key=f"modal_accept_{turn_id}_{i}"):
                    result = add_span_annotation(
                        suggestion["turn_id"],
                        suggestion["text"],
                        suggestion.get("start", 0),
                        suggestion.get("end", len(suggestion["text"])),
                        suggestion["suggested_label"],
                    )
                    if result:
                        st.session_state.ai_suggestions = [
                            s
                            for s in st.session_state.ai_suggestions
                            if not (
                                s["turn_id"] == suggestion["turn_id"]
                                and s["text"] == suggestion["text"]
                            )
                        ]
                        st.rerun()
                    else:
                        st.warning("Already exists!")
            with c2:
                if st.button("Reject", key=f"modal_reject_{turn_id}_{i}"):
                    st.session_state.ai_suggestions = [
                        s
                        for s in st.session_state.ai_suggestions
                        if not (
                            s["turn_id"] == suggestion["turn_id"]
                            and s["text"] == suggestion["text"]
                        )
                    ]
                    st.rerun()
    else:
        st.caption("No suggestions yet. Click Generate to get AI suggestions.")
