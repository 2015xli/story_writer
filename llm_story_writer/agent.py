from google.adk.agents import LoopAgent, LlmAgent, SequentialAgent, BaseAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from typing_extensions import override
from google.genai import types
import logging

logger = logging.getLogger(__name__)

# --- Constants ---
APP_NAME = "story_writing_assistant" # New App Name
USER_ID = "user_01"
SESSION_ID_BASE = "loop_exit_tool_session" # New Base Session ID
LLM_MODEL = LiteLlm(model = "deepseek/deepseek-chat")
# --- State Keys ---
STATE_CURRENT_TOPIC = "current_topic"
STATE_REFINED_TOPIC = "refined_topic"
STATE_CURRENT_DOC = "current_document"
STATE_CURRENT_TITLE = "current_title"
STATE_CRITICISM = "criticism"
# Define the exact phrase the Critic should use to signal completion
COMPLETION_PHRASE = "No major issues found."

def exit_loop(topic: str, tool_context: ToolContext):
  """Call this function ONLY when the critique indicates no further changes are needed.
  
  Args:
    topic: The topic of the story.

  Returns: Empty dict
  """
  logger.info(f"[Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  # Return empty dict as tools should typically return JSON-serializable output
  return {}

# --- Agent Definitions ---

# STEP 1: Initial Writer Agent (Runs ONCE at the beginning)
initial_writer_agent = LlmAgent(
    name="InitialWriterAgent",
    model=LLM_MODEL,
    include_contents= 'none',
    instruction=f"""You are a Creative Writing Assistant tasked with starting a flash short story.
    Write the *first draft* of a short story (aim for 3-6 sentences) based only on the prompt.
    Try to introduce a specific element (like a character, a setting detail, or a starting action) to make it engaging.
    Output *only* the story text. Do not add introductions or explanations.
    Make sure the story is interesting and engaging.
    """,
    description="Writes the initial story based on the topic, aiming for some initial substance.",
    output_key=STATE_CURRENT_DOC
)

# STEP 2a: Critic Agent (Inside the Refinement Loop)
critic_agent_in_loop = LlmAgent(
    name="CriticAgent",
    model=LLM_MODEL,
    include_contents='none',
    instruction=f"""You are a Constructive Critic AI reviewing a short story draft (typically 3-6 sentences) for a flash story. Your goal is to help the writer improve the story.
    **Story to Review:**
    ```
    {{current_document}}
    ```

    **Task:**
    Review the story for clarity, engagement, and  coherence according to the initial topic and theme.

    IF you identify 1-2 *clear and actionable* ways the story could be improved to better capture the topic or enhance reader engagement 
    (e.g., "Needs a stronger opening sentence", 
    "Clarify the character's goal", 
    "Plot twist is too simple", 
    "Need more conflicts", 
    "Closing statement is not a real cliffhanger"):
    Provide these specific suggestions concisely. Output *only* the critique text.


    ELSE IF the story is coherent, addresses the topic adequately for its length, and has no glaring errors or obvious omissions:
    Respond *exactly* with the phrase "{COMPLETION_PHRASE}" and nothing else. 

    Do not add explanations. Output only the critique OR the exact completion phrase.
""",
    description="Reviews the current story, providing critique if clear improvements are needed, otherwise signals completion.",
    output_key=STATE_CRITICISM
)


# STEP 2b: Refiner/Exiter Agent (Inside the Refinement Loop)
refiner_agent_in_loop = LlmAgent(
    name="RefinerAgent",
    model=LLM_MODEL,
    # Relies solely on state via placeholders
    include_contents='none',
    instruction=f"""You are a Creative Writing Assistant refining a story based on critique OR exiting the process.

    **Topic and Theme:**
    ```{{current_topic}}```
    
    **Current Story:**
    ```
    {{current_document}}
    ```
    
    **Critique/Suggestions:**
    ```
    {{criticism}}
    ```
    **Task:**
    Analyze the 'Critique/Suggestions'.
    IF the critique is *exactly* "{COMPLETION_PHRASE}":
    You MUST call the 'exit_loop' function with the current topic as the argument. Do not output any text.
    ELSE (the critique contains actionable feedback):
    Carefully apply the suggestions to improve the 'Current Story'. Output *only* the refined story text.

    Do not add explanations. Either output the refined story OR call the exit_loop function.
""",
    description="Refines the story based on critique, or calls exit_loop if critique indicates completion.",
    tools=[exit_loop], # Provide the exit_loop tool
    output_key=STATE_CURRENT_DOC # Overwrites state['current_document'] with the refined version
)


# Create internal agents *before* calling super().__init__
# STEP 2: Refinement Loop Agent
story_refinement_loop = LoopAgent(
    name="StoryRefinementLoop",
    sub_agents=[
        critic_agent_in_loop,
        refiner_agent_in_loop,
    ],
    max_iterations=5 # Limit loops
)

# STEP 3: Overall Sequential Pipeline
# For ADK tools compatibility, the root agent must be named `root_agent`
story_writing_pipeline = SequentialAgent(
    name="StoryWritingPipeline",
    sub_agents=[
        initial_writer_agent, # Run second to create initial doc
        story_refinement_loop       # Then run the critique/refine loop
    ],
    description="Writes an initial document and then iteratively refines it with critique using an exit tool."
)


 # Story writing assistant
root_agent = LlmAgent(
    name="StoryWritingAssistant",
    model=LLM_MODEL,
    include_contents='default',
    instruction=f"""You are a story writing assistant to help the user write a flash story.
                Your main task is to look at the conversation history with the user to extract story topic and theme.
                Example topics: a person who wants to save the city with his friends, a programmer was rejected by his girlfriend.
                Example themes: fantasy, science fiction, horror, romance, comedy, drama, thriller, mystery, young adult, middle grade.

                If either topic or theme is missing from the conversation:
                - Ask the user specifically to get the missing parts (topic or theme or both).
                If you have identified BOTH a clear topic and a valid theme from the conversation:
                - You must output the topic and theme to get user's ok.
                If you've got the user's ok, then you should pass the topic and theme to your sub-agent story_writing_pipeline, who will generate the story. 
                - The format is "STORY: [topic: [user's topic], theme: [user's theme]]". Do not output any additional text.
                """,
    description="A flash story writing assistant to help the user write a flash story.",
    sub_agents=[
        story_writing_pipeline
    ],
    output_key=STATE_CURRENT_TOPIC,
)
    
