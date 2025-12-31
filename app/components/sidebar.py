"""Sidebar component for BBN Annotation Tool."""

import json
import streamlit as st

from config import OPENAI_MODELS, ANTHROPIC_MODELS, USE_DATABASE
from state import update_agent_config
from services.data_service import (
    load_conversations,
    load_existing_annotations,
    save_annotations,
    get_current_expert,
    get_all_experts,
)


def render_sidebar(schema):
    """Render the sidebar and return the current conversation."""
    st.sidebar.title("BBN Annotation Tool")

    # Database status indicator
    if USE_DATABASE:
        st.sidebar.caption("Database: Enabled")
    else:
        st.sidebar.caption("Mode: JSON files only")

    st.sidebar.markdown("---")

    # Expert selector (if using database)
    if USE_DATABASE:
        experts = get_all_experts()
        current_expert = get_current_expert()

        if len(experts) > 1:
            expert_options = {e["name"]: e for e in experts}
            selected_expert_name = st.sidebar.selectbox(
                "Expert",
                options=list(expert_options.keys()),
                index=list(expert_options.keys()).index(current_expert["name"]) if current_expert["name"] in expert_options else 0,
            )
            st.session_state.current_expert = expert_options[selected_expert_name]
        else:
            st.sidebar.caption(f"Expert: {current_expert['name']}")

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
            expert_id = st.session_state.get("current_expert", {}).get("id") if USE_DATABASE else None
            annotations = load_existing_annotations(current_conv, expert_id)
            st.session_state.current_annotations = annotations
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
            expert_id = st.session_state.get("current_expert", {}).get("id") if USE_DATABASE else None
            success = save_annotations(
                current_conv,
                st.session_state.current_annotations,
                expert_id,
            )
            if success:
                st.sidebar.success("Saved to database!" if USE_DATABASE else "Saved!")
            else:
                st.sidebar.error("Save failed")

    # Export button
    if current_conv:
        from services.data_service import _merge_annotations
        merged_conv = _merge_annotations(current_conv.copy(), st.session_state.current_annotations)
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
