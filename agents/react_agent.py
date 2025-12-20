"""
ReAct Annotation Agent

A single agent that uses ReAct (Reasoning + Acting) to annotate
Breaking Bad News conversations step by step.
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .base import (
    AgentConfig,
    AnnotationResult,
    TurnAnnotation,
    SpanAnnotation,
    RelationAnnotation,
    Speaker,
    get_labels_for_speaker,
    generate_span_id,
    SPIKES_STAGES,
)
from .prompts import (
    REACT_SYSTEM_PROMPT,
    REACT_USER_PROMPT_TEMPLATE,
    RELATION_USER_PROMPT_TEMPLATE,
)


@dataclass
class ReActStep:
    """A single ReAct reasoning step"""
    thought: str
    action: str
    observation: str


class LLMClient:
    """Wrapper for LLM API calls - supports OpenAI and Anthropic"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.config.provider == "openai":
                from openai import OpenAI
                self._client = OpenAI(api_key=self.config.api_key)
            elif self.config.provider == "anthropic":
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.config.api_key)
        return self._client

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat request to the LLM"""
        client = self._get_client()

        if self.config.provider == "openai":
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content

        elif self.config.provider == "anthropic":
            response = client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.content[0].text

        raise ValueError(f"Unknown provider: {self.config.provider}")


class ReActAnnotationAgent:
    """
    ReAct Agent for BBN Conversation Annotation

    Uses Reasoning + Acting pattern to:
    1. Think about what annotations might exist
    2. Identify specific spans
    3. Verify and refine annotations
    4. Output final structured result
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.llm = LLMClient(self.config)

    def annotate_conversation(
        self,
        conversation: Dict[str, Any],
        include_relations: bool = True
    ) -> AnnotationResult:
        """
        Annotate an entire conversation.

        Args:
            conversation: Conversation dict with 'id', 'metadata', 'turns'
            include_relations: Whether to identify relations between spans

        Returns:
            AnnotationResult with all annotations
        """
        conversation_id = conversation.get("id", "unknown")
        turns = conversation.get("turns", [])

        annotated_turns: List[TurnAnnotation] = []
        all_patient_eos: List[Dict] = []
        all_clinician_responses: List[Dict] = []

        # Process each turn
        for i, turn in enumerate(turns):
            # Build context from previous turns
            context = self._build_context(turns[:i])

            # Annotate the turn
            turn_annotation = self._annotate_turn(turn, context)
            annotated_turns.append(turn_annotation)

            # Collect spans for relation linking
            for span in turn_annotation.spans:
                span_info = {
                    "turn_id": turn_annotation.turn_id,
                    "span_id": span.span_id,
                    "text": span.text,
                    "label": span.label,
                }
                if turn_annotation.speaker == Speaker.PATIENT:
                    all_patient_eos.append(span_info)
                else:
                    all_clinician_responses.append(span_info)

        # Identify relations if requested
        if include_relations and all_patient_eos and all_clinician_responses:
            relations = self._identify_relations(
                all_patient_eos,
                all_clinician_responses,
                turns
            )
            # Attach relations to relevant turns
            self._attach_relations(annotated_turns, relations)

        return AnnotationResult(
            conversation_id=conversation_id,
            turns=annotated_turns,
            agent_type="react",
            metadata={
                "model": self.config.model,
                "provider": self.config.provider,
            }
        )

    def annotate_turn(
        self,
        turn: Dict[str, Any],
        context: str = ""
    ) -> TurnAnnotation:
        """
        Annotate a single turn (public interface).

        Args:
            turn: Turn dict with 'turn_id', 'speaker', 'text'
            context: Previous conversation context

        Returns:
            TurnAnnotation with spans and SPIKES stage
        """
        return self._annotate_turn(turn, context)

    def _annotate_turn(
        self,
        turn: Dict[str, Any],
        context: str
    ) -> TurnAnnotation:
        """Internal method to annotate a single turn"""
        turn_id = turn.get("turn_id", 0)
        speaker_str = turn.get("speaker", "patient").lower()
        speaker = Speaker(speaker_str)
        text = turn.get("text", "")

        # Build the prompt
        user_prompt = REACT_USER_PROMPT_TEMPLATE.format(
            turn_id=turn_id,
            speaker=speaker_str,
            text=text,
            context=context if context else "No previous context."
        )

        # Call the LLM
        response = self.llm.chat(REACT_SYSTEM_PROMPT, user_prompt)

        # Parse the response
        parsed = self._parse_response(response)

        # Build span annotations
        spans: List[SpanAnnotation] = []
        for i, ann in enumerate(parsed.get("annotations", [])):
            # Validate span positions
            start = ann.get("start", 0)
            end = ann.get("end", len(ann.get("text", "")))
            span_text = ann.get("text", "")

            # Verify the span exists in the text
            if span_text and span_text in text:
                actual_start = text.find(span_text)
                if actual_start != -1:
                    start = actual_start
                    end = actual_start + len(span_text)

            span = SpanAnnotation(
                span_id=generate_span_id(turn_id, i),
                text=span_text,
                start=start,
                end=end,
                label=ann.get("label", "unknown"),
                reasoning=ann.get("reasoning", ""),
            )
            spans.append(span)

        # Get SPIKES stage (only for clinician)
        spikes_stage = None
        if speaker == Speaker.CLINICIAN:
            spikes_stage = parsed.get("spikes_stage")
            if spikes_stage and spikes_stage not in SPIKES_STAGES:
                spikes_stage = None

        return TurnAnnotation(
            turn_id=turn_id,
            speaker=speaker,
            text=text,
            spikes_stage=spikes_stage,
            spans=spans,
            relations=[],
        )

    def _identify_relations(
        self,
        patient_eos: List[Dict],
        clinician_responses: List[Dict],
        turns: List[Dict]
    ) -> List[RelationAnnotation]:
        """Identify relations between patient EOs and clinician responses"""

        # Build conversation summary
        conversation_summary = "\n".join([
            f"Turn {t['turn_id']} ({t['speaker']}): {t['text'][:100]}..."
            for t in turns
        ])

        # Format EOs and responses
        eo_text = json.dumps(patient_eos, indent=2)
        response_text = json.dumps(clinician_responses, indent=2)

        user_prompt = RELATION_USER_PROMPT_TEMPLATE.format(
            patient_eos=eo_text,
            clinician_responses=response_text,
            conversation=conversation_summary
        )

        # Use a simplified system prompt for relations
        system_prompt = """You are an expert at identifying semantic relationships
        between patient expressions and clinician responses in medical conversations.
        Identify clear connections between clinician responses/elicitations and patient
        empathic opportunities."""

        response = self.llm.chat(system_prompt, user_prompt)
        parsed = self._parse_response(response)

        relations: List[RelationAnnotation] = []
        for rel in parsed.get("relations", []):
            relation = RelationAnnotation(
                from_span_id=rel.get("from_span_id", ""),
                to_span_id=rel.get("to_span_id", ""),
                relation_type=rel.get("relation_type", "response_to"),
            )
            relations.append(relation)

        return relations

    def _attach_relations(
        self,
        turns: List[TurnAnnotation],
        relations: List[RelationAnnotation]
    ):
        """Attach relations to the appropriate turns"""
        # Create a map of span_id to turn
        span_to_turn: Dict[str, TurnAnnotation] = {}
        for turn in turns:
            for span in turn.spans:
                span_to_turn[span.span_id] = turn

        # Attach each relation to the turn containing the 'from' span
        for relation in relations:
            if relation.from_span_id in span_to_turn:
                turn = span_to_turn[relation.from_span_id]
                turn.relations.append(relation)

    def _build_context(self, previous_turns: List[Dict], max_turns: int = 5) -> str:
        """Build context string from previous turns"""
        if not previous_turns:
            return ""

        recent_turns = previous_turns[-max_turns:]
        context_parts = []
        for turn in recent_turns:
            speaker = turn.get("speaker", "unknown")
            text = turn.get("text", "")[:200]  # Truncate long texts
            context_parts.append(f"{speaker.upper()}: {text}")

        return "\n".join(context_parts)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON"""
        # Try to find JSON in the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try to parse the whole response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Return empty result if parsing fails
        return {"annotations": [], "spikes_stage": None}


# Convenience function
def create_react_agent(
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> ReActAnnotationAgent:
    """
    Create a ReAct annotation agent with the specified configuration.

    Args:
        provider: "openai" or "anthropic"
        model: Model name (defaults to gpt-4o or claude-3-5-sonnet)
        api_key: API key (uses environment variable if not provided)
        **kwargs: Additional AgentConfig parameters

    Returns:
        Configured ReActAnnotationAgent
    """
    if model is None:
        model = "gpt-4o" if provider == "openai" else "claude-3-5-sonnet-20241022"

    config = AgentConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        **kwargs
    )
    return ReActAnnotationAgent(config)
