# Story Writer Agent

This repository contains two implementations of an AI-powered story writing assistant, both built using the Google ADK (Agent Development Kit) framework. Each implementation takes a unique approach to creating and refining short stories through an interactive, multi-agent workflow.

## Implementations

### 1. LLM Story Writer (`llm_story_writer/`)

A streamlined implementation that focuses on using a single root agent design that works seamlessly with both `adk run` and `adk web` commands without requiring custom runner or session management code.

**Key Features:**
- Single root agent design for simplified interaction
- Works with both CLI and web interfaces
- Automatic story refinement through critic-refiner loop
- Clean separation of concerns between different writing stages

**Best for:** Users who want a simple, out-of-the-box solution that works with standard ADK commands.

### 2. Custom Story Writer (`custom_story_writer/`)

A more advanced implementation that provides greater control over the story creation workflow through a custom agent implementation with direct console interaction.

**Key Features:**
- Custom agent implementation with fine-grained control
- Direct console interaction for gathering story requirements
- More flexible architecture for customization
- Detailed state management

**Best for:** Developers who need more control over the agent's behavior and are comfortable with a more complex implementation.

## Getting Started

### Prerequisites

- Python 3.13+
- Google ADK (Agent Development Kit)
- LLM API access with LiteLLM (e.g., OpenAI, Anthropic, DeepSeek)

### Installation

1. Clone the repository
2. Install dependencies
3. Set up your LLM API key (e.g., `export DEEPSEEK_API_KEY=your_api_key`)

### Running the Agents

#### LLM Story Writer
```bash
adk run llm_story_writer
# or
adk web
```

#### Custom Story Writer
```bash
adk run custom_story_writer
```

## Choosing the Right Implementation

- **LLM Story Writer** is recommended if you want a simple, standard implementation that works well with both CLI and web interfaces.
- **Custom Story Writer** is an experiment for people who want to understand more about Google ADK agent design. Not recommended.

