"""AI agent integration services."""

import os
import streamlit as st


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
            suggestions.append({
                "turn_id": turn_id,
                "text": span.text,
                "start": span.start,
                "end": span.end,
                "suggested_label": span.label,
                "reasoning": span.reasoning,
            })
        return suggestions

    # Handle AnnotationResult
    if hasattr(agent_result, "turns"):
        for turn in agent_result.turns:
            if turn.turn_id == turn_id:
                for span in turn.spans:
                    suggestions.append({
                        "turn_id": turn_id,
                        "text": span.text,
                        "start": span.start,
                        "end": span.end,
                        "suggested_label": span.label,
                        "reasoning": span.reasoning,
                    })

    return suggestions
