# Story Writing Agent

An AI-powered agent for generating and refining short stories through an interactive, multi-agent workflow. This system uses a pipeline of specialized AI agents to create engaging flash fiction based on user-provided topics and themes.

## Overview

The Story Writing Agent is built using the Google ADK (Agent Development Kit) framework and implements a multi-agent architecture where different AI agents handle specific aspects of the story creation process. The system guides users through topic collection, initial story generation, and iterative refinement based on AI critique. 

It is based on Google ADK example code, but with enhancements to make it more user-friendly and interactive. What it really experiments with is how to interact with the user in a single root agent design that can run with "adk run" without writing your own runner and session management code.

## Features

- **Interactive Topic Collection**: Conversational interface to gather story topics and themes
- **AI-Powered Story Generation**: Creates initial story drafts based on user input
- **Iterative Refinement**: Uses a critic-refiner loop to improve story quality

## Architecture

The system is composed of several specialized agents working together:

1. **VibeWritingAgent**: Main orchestrator (the root_agent) that manages the story creation workflow
2. **TopicCollectorAgent**: Handles initial topic and theme collection from the user interactively
3. **InitialWriterAgent**: Generates the first draft of the story
4. **CriticAgent**: Provides constructive feedback on the current story draft
5. **RefinerAgent**: Implements suggested improvements to the story

VibeWritingAgent (custom agent) is the root agent that orchestrates the entire story creation process. It has sub_agents instance attribute that is a list of agents, including a topic_collector_agent (LlmAgent), and a story_writing_pipeline (SequentialAgent). The story_writing_pipeline includes initial_writer_agent (LlmAgent) and story_refinement_loop (LoopAgent). The story_refinement_loop includes a critic_agent_in_loop (LlmAgent) and a refiner_agent_in_loop (LlmAgent) in the loop. 

The hierarchy of the agents is as follows:

```
root_agent (VibeWritingAgent) 
  └-subagents
        └- topic_collector_agent (LlmAgent)
        └- story_writing_pipeline (SequentialAgent)
                └- initial_writer_agent (LlmAgent)
                └- story_refinement_loop (LoopAgent)
                        └- critic_agent_in_loop (LlmAgent)
                        └- refiner_agent_in_loop (LlmAgent)
```

## Requirements

- Python 3.13+
- Google ADK (Agent Development Kit)
- LLM API access with LiteLLM (e.g. OpenAI, Anthropic, DeepSeek, etc. The code use DeepSeek by default. API key is required.)

## Configuration

Key configuration options in `agent.py`:

- `LLM_MODEL`: The language model used (default: "deepseek/deepseek-chat")
- Export api key in the environment variable, such as DEEPSEEK_API_KEY=your_api_key

## Usage

1. Run the agent in the project directory after you have cloned the repository and installed the dependencies:
   ```bash
   adk run .
   ```
   If you run with "adk web", you need go to the parent directory of the project directory instead. But "adk web" method is not recommended. The reason is explained at the bottom section.
2. Follow the interactive prompts to provide a story topic and theme
3. The system will generate a story based on the topic and theme

## Design Notes

The whole coordination logic is implemented in the _run_async_impl method of VibeWritingAgent. It basically just calls the async event for loop of subagent.run_async() for each subagent in the sub_agents list. The key part is, in order to interact with the user, the first event for loop of topic_collector_agent is not just to yield event, but also to collect user input and update the session state that can be used by the topic_collector_agent itself. In order to update the session state for it to be used in the next event generation, a session state "init_topic" is used to record the user's input. The state variable {{init_topic}} is used in the topic_collector_agent's instruction.

Since the code in _run_async_impl can only interact with user directly over console - this is like an interaction backdoor to the agent, without going through the session manager. This approach can use "adk run", but not "adk web", because "adk run" uses console for direct interaction. User cannot see the difference between the backdoor interaction and "adk run" session interaction. They are actually two things mixed together.

On the other hand, "adk web" wraps the agent session in a fastAPI server, and user interacts with the agent through a frontend webpage. Since _run_async_impl's interaction is not wrapped in the fastAPI session, the backdoor interaction and the webpage interaction are separated.

(Btw, when running with "adk web", if it needs user input, it outputs to the console, and waiting for user input there. So the backdoor console can still be used to interact with the agent.)
