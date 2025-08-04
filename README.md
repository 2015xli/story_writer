# Story Writer Agent

This repository contains three implementations of an AI-powered story writing assistant, both built using the Google ADK (Agent Development Kit) framework. Each implementation takes a unique approach to creating and refining short stories through an interactive, `MULTI_TURN`, multi-agent workflow.

## Implementations

### 1. LLM Story Writer (`llm_story_writer/`)

A streamlined implementation that focuses on using a single root agent design that works seamlessly with `adk run`. For `adk web`, you have to use both the web page and console to interact with the agents.

**Key Features:**
- Single root agent design for simplified interaction
- Works with both CLI and web interfaces
- Automatic story refinement through critic-refiner loop
- Clean separation of concerns between different writing stages

**Best for:** Users who want a simple, out-of-the-box solution that works with standard ADK commands.

### 2. Interactive Story Writer (`interact_story_writer/`)

A more advanced implementation that leverages a loop agent and a callback function to interact with the user in the console to collect story requirements. It works with both `adk run` and `adk web` commands.

**Key Features:**
- Loop agent design for interactive multi-turn story collection
- Callback function for user interaction
- This is the recommended way by Google ADK for human-in-the-loop interaction.

**Best for:** Users who want a recommended way by Google ADK for human-in-the-loop interaction. You can hook whatever UI you want to the callback function.

### 3. Custom Story Writer (`custom_story_writer/`)

An even more advanced implementation that provides greater control over the story creation workflow through a custom agent implementation with direct console interaction.

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

#### Interactive Story Writer
```bash
adk run interact_story_writer
```
or
```bash
adk web
```
And interact in both web page and console.

#### Custom Story Writer
```bash
adk run custom_story_writer
```
or
```bash
adk web
```
And interact in both web page and console.

## Choosing the Right Implementation

- **LLM Story Writer** is recommended if you want a simple, standard implementation that works well with both CLI and web interfaces.
- **Interactive Story Writer** is recommended if you want a recommended way by Google ADK for human-in-the-loop interaction. You can hook whatever UI you want to the callback function.
- **Custom Story Writer** is an experiment for people who want to understand more about Google ADK agent design. Not recommended.

