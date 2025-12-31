"""Sidebar component for BBN Annotation Tool."""

import json
import streamlit as st

from config import OPENAI_MODELS, ANTHROPIC_MODELS
from state import update_agent_config
from services import (
    load_conversations,
    load_existing_annotations,
    merge_annotations_to_conversation,
    save_conversation,
)


def render_sidebar(schema):
    """Render the sidebar and return the current conversation."""
    st.sidebar.title("BBN Annotation Tool")
    st.sidebar.markdown("---")

    # Load conversations
    conversations = load_conversations()

    # Conversation selector
    st.sidebar.subheader("Conversations")
    current_conv = None

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

    # Agent configuration
    st.sidebar.markdown("---")
    st.sidebar.subheader("AI Agent")

    agent_type = st.sidebar.selectbox(
        "Agent Type",
        ["react", "multi"],
        format_func=lambda x: "ReAct Agent" if x == "react" else "Multi-Agent",
    )

    provider = st.sidebar.selectbox("Provider", ["openai", "anthropic"])

    if provider == "openai":
        model = st.sidebar.selectbox("Model", OPENAI_MODELS)
    else:
        model = st.sidebar.selectbox("Model", ANTHROPIC_MODELS)

    update_agent_config(provider, model, agent_type)

    # Save button
    st.sidebar.markdown("---")
    if st.sidebar.button("Save Annotations", type="primary", use_container_width=True):
        if current_conv:
            merged_conv = merge_annotations_to_conversation(current_conv.copy())
            save_conversation(merged_conv, current_conv.get("filepath"))
            st.sidebar.success("Saved!")

    # Export button
    if current_conv:
        merged_conv = merge_annotations_to_conversation(current_conv.copy())
        st.sidebar.download_button(
            label="Export JSON",
            data=json.dumps(merged_conv, indent=2, ensure_ascii=False),
            file_name=f"annotated_{current_conv.get('id', 'unknown')}.json",
            mime="application/json",
            use_container_width=True,
        )

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("AI-Assisted Clinical Annotation")

    return current_conv
