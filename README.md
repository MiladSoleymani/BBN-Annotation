# BBN Annotation Tool

A Streamlit-based viewer and annotation tool for Breaking Bad News (BBN) conversations, based on the Appraisal Framework for Clinical Empathy.

## Features

- **Conversation Viewer**: View BBN conversations with highlighted annotations
- **Annotation Schema Reference**: Interactive guide to the annotation framework
- **Statistics Dashboard**: Visualize annotation distributions and patterns
- **Color-coded Highlights**: Easily identify different types of empathic elements

## Project Structure

```
BBN-Annotation/
├── app/
│   └── main.py              # Main Streamlit application
├── data/
│   ├── samples/             # Sample conversation files (JSON)
│   └── annotation_schema.json
├── docs/
│   ├── BBN_Framework_Summary.md
│   └── 8083_pages_93-113.pdf
├── components/              # Reusable UI components (future)
├── venv/                    # Python virtual environment
├── requirements.txt
├── run.sh                   # Run script
└── README.md
```

## Quick Start

### Option 1: Using the run script
```bash
./run.sh
```

### Option 2: Manual
```bash
# Activate virtual environment
source venv/bin/activate

# Run the app
streamlit run app/main.py
```

Then open your browser to `http://localhost:8501`

## Data Format

Conversations are stored as JSON files with the following structure:

```json
{
  "id": "conv_001",
  "metadata": {
    "scenario": "MRI finding - brain mass",
    "language": "en"
  },
  "turns": [
    {
      "turn_id": 1,
      "speaker": "clinician",
      "text": "Hello, I'm Dr. Smith...",
      "annotations": {
        "spikes_stage": "setting",
        "spans": [...],
        "relations": [...]
      }
    }
  ]
}
```

## Annotation Schema

### Patient: Empathic Opportunities (EOs)
| Type | Explicit | Implicit |
|------|----------|----------|
| Feelings | Direct emotions | Indirect via experiences |
| Appreciation | Direct attitudes toward things | Indirect attitudes |
| Judgement | Direct attitudes toward self/others | Indirect attitudes |

### Clinician: Responses
- **Acceptance**: Positive regard, neutral support
- **Sharing**: Expressing agreement with patient
- **Understanding**: Acknowledging patient views/feelings
- **Elicitations**: Prompting patient expressions

### SPIKES Protocol
- **S**etting - Environment setup
- **P**erception - Patient knowledge assessment
- **I**nvitation - Information readiness
- **K**nowledge - Delivering information
- **E**mpathy - Emotional response
- **S**trategy - Treatment planning

## Adding New Conversations

1. Create a JSON file in `data/samples/`
2. Follow the data format structure above
3. Refresh the app to see the new conversation

## Future Development

- [ ] AI-assisted annotation suggestions
- [ ] Export annotations
- [ ] Multi-annotator support
- [ ] Inter-annotator agreement metrics

## References

Based on:
- Lahnala et al. (2024). "Appraisal Framework for Clinical Empathy: A Novel Application to Breaking Bad News Conversations." LREC-COLING 2024.
- Pounds, G. (2011). Appraisal Framework for Clinical Empathy
- Baile et al. (2000). SPIKES Protocol for Breaking Bad News

## License

Research use only.
