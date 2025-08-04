# Story Writing Assistant Agent

An AI-powered story writing assistant that helps users create and refine short stories through an iterative writing and refinement process.

## Overview

This agent implements a multi-agent system for generating and refining short stories. It uses a pipeline of specialized AI agents to:
1. Understand the user's story requirements (topic and theme)
2. Generate an initial story draft
3. Iteratively refine the story through critique and revision
4. Ensure the final output meets quality standards

The code is based on Google ADK example code, but with enhancements to make it more user-friendly and interactive. What it really experiments with is how to interact with the user in a single root agent design that can run with "adk run" and "adk web" without writing your own runner and session management code.

## How It Works

The system consists of several specialized agents working together:

1. **Root Agent (StoryWritingAssistant)**
   - Interacts with the user to gather story requirements
   - Validates input and manages the writing process
   - Coordinates between different specialized agents

2. **Initial Writer Agent**
   - Generates the first draft of the story
   - Focuses on creating an engaging opening with key story elements

3. **Critic Agent**
   - Analyzes the current story draft
   - Provides constructive feedback for improvement
   - Signals when the story meets quality standards

4. **Refiner Agent**
   - Implements suggested improvements from the Critic
   - Makes targeted edits to enhance the story
   - Decides when the refinement process is complete

Hierarchy of the agents:

```
StoryWritingAssistant (LlmAgent)
    └── sub_agents
            └── story_writing_pipeline (SequentialAgent)
                    └── InitialWriterAgent (LlmAgent)
                    └── story_refinement_loop (LoopAgent)
                            └── CriticAgent (LlmAgent)
                            └── RefinerAgent (LlmAgent)
```

### Usage

In the root directory of the project, run,
```bash
 "adk run llm_story_writer".
```
or 
```bash
"adk web"
```

Then, input the topic and theme of the story. E.g.,
```
[user]: A programmer discovers their code has come to life
```

The agent will interact to get both the topic and theme are confirmed. Then it will pass the topic and theme to the story writing pipeline to generate the story.

## Requirements

- Python 3.13+
- Google ADK (Agent Development Kit)
- LLM API access with LiteLLM (e.g. OpenAI, Anthropic, DeepSeek, etc. The code use DeepSeek by default. API key is required.)

## Configuration

The agent is pre-configured to use the `deepseek/deepseek-chat` model, but this can be modified in the `agent.py` file by changing the `LLM_MODEL` constant.

## Design Notes

In order to make the agent run with "adk run" and "adk web" without writing your own runner and session management code, we use a root agent design that calls the story writing pipeline as a sub-agent.

The story writing pipeline is a SequentialAgent that calls InitialWriterAgent and story_refinement_loop as sub-agents. The story_refinement_loop is a LoopAgent that calls CriticAgent and RefinerAgent as sub-agents. Once the control is passed to the pipeline sub-agents, user will not be able to interact with the agent until it finishes the story writing. 

To make the root agent (StoryWritingAssistant) to interact with the user, we use LlmAgent for the top-level agent StoryWritingAssistant. The interaction only happens before it transfers its control to the story writing pipeline (SequentialAgent) as a sub-agent. Every interaction with the user is an independent invocation of the root agent, and the invocation either stops before it transfers its control to the story writing pipeline, or it stops after the story writing pipeline is finished. 

Based on this idea, we can consider a way to early return from a sub-agent in the pipeline, so as to make the invocation stop at any point in the pipeline. A possible way is to use a custom agent that yields an escalation event.
