# Interactive Story Writing Assistant

An AI-powered story writing assistant that helps users create and refine short stories through an interactive, multi-agent process.

## Overview

This system implements a sophisticated pipeline of specialized AI agents that work together to:
1. Collect and validate story requirements (topic and theme)
2. Generate an initial story draft
3. Iteratively refine the story through automated critique and revision
4. Ensure the final output meets quality standards

The implementation uses Google's Agent Development Kit (ADK) with a focus on creating a seamless user experience through a single root agent design that works with both `adk run` and `adk web` commands.

## How It Works

The system consists of several specialized agents working in sequence:

### 1. Topic Collection Loop
- **Topic Collector Agent**: Interacts with the user to gather story requirements
  - Extracts topic and theme from user input
  - Validates that both components are present
  - Formats the input for the next stage

- **Topic Confirmation Agent**: Validates the collected information
  - Ensures both topic and theme are properly specified
  - Uses the `exit_sequence` tool when requirements are met
  - Triggers clarification requests when information is missing

### 2. Story Generation Phase
- **Initial Writer Agent**: Creates the first draft
  - Generates a 3-6 sentence story based on the provided topic and theme
  - Focuses on creating an engaging opening with key story elements

### 3. Refinement Loop
- **Critic Agent**: Analyzes the current draft
  - Provides 1-2 specific, actionable suggestions for improvement
  - Uses a special completion phrase ("No major issues found") to signal satisfaction

- **Refiner Agent**: Implements suggested improvements
  - Makes targeted edits based on critic feedback
  - Decides when the refinement process is complete

## Agent Hierarchy

```
   
story_writing_pipeline (SequentialAgent)
      ├── topic_collector_loop (LoopAgent)
      |      ├── topic_collector_agent (LlmAgent)
      |      └── topic_confirm_agent (LlmAgent)
      ├── initial_writer_agent (LlmAgent)
      └── story_refinement_loop (LoopAgent)
            ├── critic_agent_in_loop (LlmAgent)
            └── refiner_agent_in_loop (LlmAgent)
```

## Usage

### Prerequisites
- Python 3.13+
- Google ADK (Agent Development Kit)
- LiteLLM with access to an LLM API (default: DeepSeek)

### Running the Agent

1. In this project directory, run:
   ```bash
   adk run .
   ```

2. When prompted, provide a story topic and theme. For example:
   ```
   [user]: A programmer discovers their code has come to life
   ```

The agent will guide you through the process, asking for clarification if needed, and then generate and refine your story automatically.

## Configuration

The agent is pre-configured to use the `deepseek/deepseek-chat` model. To change this, modify the `LLM_MODEL` constant in `agent.py`.

## Design Notes

The system uses a combination of `LoopAgent` and `SequentialAgent` to create a controlled flow.

Since an agent in Google ADK does not provide multi-turn human-in-the-loop interaction, we use a loop agent design that calls the story topic collector agent multiple times when collecting the story topic and theme. In the loop, the story topic collector agent generates the topic and theme in the first turn, and the topic confirmation agent validates the topic and theme in the second turn. If the topic and theme are valid, the loop agent will exit the loop and continue to the next stage; otherwise, the loop continues to the next iteration, then the story topic collector agent will generate the topic and theme again. 

In order for the topic confirmation agent to validate the topic and theme, we use after_model_callback "topic_clarification" that will interact with the user in the console to ask the user to input additional information. The additional information will be appended to a session state "current_topic" to record user inputs, so that the topic collector agent can use the session state to generate the topic and theme in the next iteration. 

If you run the agent with "adk run", then everything looks normal. If you run the agent with "adk web", then the interaction in the callback function is a backdoor through console. The reason is that "adk web" has its own session management that is wrapped in a fastAPI server and user interaction is through a frontend webpage. The callback function is not wrapped in the fastAPI session, so its interaction is separated from the "adk web" session interaction. 