from google.adk.agents import LoopAgent, LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.models.llm_request import LlmRequest
from google.genai import types
import logging, copy
from google.adk.agents.callback_context import CallbackContext
from typing import Optional

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

def exit_sequence(requirement: str, tool_context: ToolContext):
  """Call this function ONLY when the user requirement has clear topic and theme.
     If the requirement is not in the required format, don't call the function, since it means the requirement is missing either topic or theme.
  Args:
    requirement: The requirement of the story.

  Returns: Empty dict
  """
  logger.info(f"[Tool Call] exit_sequence triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  
  # Return empty dict as tools should typically return JSON-serializable output
  return f"You have provided information for topic AND theme."

def topic_collection(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmRequest]:

    """Inspects/modifies the LLM request or skips the call."""
    agent_name = callback_context.agent_name
    print(f"[Callback] Before model call for agent: {agent_name}")

    # Inspect the last user message in the request contents
    last_user_message = ""
    if llm_request.contents and llm_request.contents[-1].role == 'user':
         if llm_request.contents[-1].parts:
            last_user_message = llm_request.contents[-1].parts[0].text
            print(f"[Callback] Inspecting last user message: '{last_user_message}'")
            topic = callback_context.state.get(STATE_CURRENT_TOPIC, "")

            if last_user_message and "EXIT" not in last_user_message.upper() and topic != "":
                print(f"[Callback] Changing last user message: '{topic}'")
                llm_request.contents[-1].parts[0].text = topic
                # should not return llm_request here, because ADK thinks it's llm_response.

    # Return None to allow the (modified) request to go to the LLM
    return None

def topic_clarification(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:

    """Inspects/modifies the LLM response after it's received."""
    agent_name = callback_context.agent_name
    print(f"[Callback] After model call for agent: {agent_name}")

    # --- Inspection ---
    original_text = ""
    if llm_response.content and llm_response.content.parts:
        # Assuming simple text response for this example
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            print(f"[Callback] Inspected original response text: '{original_text[:100]}...'") # Log snippet
        elif llm_response.content.parts[0].function_call:
            print(f"[Callback] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification.")
            return None # Don't modify tool calls in this example
        else:
            print("[Callback] Inspected response: No text content found.")
            return None
    elif llm_response.error_message:
        print(f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
        return None
    else:
        print("[Callback] Inspected response: Empty LlmResponse.")
        return None # Nothing to modify

    # --- Get user's inputs and modify the response
    search_item = "additional information"
    if search_item in original_text.lower():
        topic = callback_context.state.get(STATE_CURRENT_TOPIC, "")
        print(f"Your originial info is incomplete. {topic}")
        print(f"Please provide the missing part.")
        print("[user]:", end="")
        new_topic = input().strip()

        # Create a NEW LlmResponse with the modified content
        # Deep copy parts to avoid modifying original if other callbacks exist
        if 'exit' == new_topic:
            modified_text = new_topic
        else:
            modified_text = topic + ". With additional information: " + new_topic

        callback_context.state[STATE_CURRENT_TOPIC] = modified_text

        modified_parts = [copy.deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = modified_text # Update the text in the copied part

        new_response = LlmResponse(
             content=types.Content(role="model", parts=modified_parts),
             # Copy other relevant fields if necessary, e.g., grounding_metadata
             grounding_metadata=llm_response.grounding_metadata
             )
        print(f"[Callback] Returning modified response.")
        return new_response # Return the modified response
    else:
        print(f"[Callback] '{search_item}' not found. Passing original response through.")
        # Return None to use the original llm_response
        return None

# --- Agent Definitions ---
# STEP 0a: Topic Collector Agent
topic_collector_agent = LlmAgent(
    name="TopicCollectorAgent",
    model=LLM_MODEL,
    include_contents='default',
    instruction=f"""You are collecting topic and theme for a flash story.
                Look at the full conversation history and the following requirements to extract topic and theme from the user input.
                Example topics: a person who wants to save the city with his friends, a programmer was rejected by his girlfriend.
                Example themes: fantasy, science fiction, horror, romance, comedy, drama, thriller, mystery, young adult, middle grade.

                IF the user provides BOTH a clear topic and a valid theme,
                - You should respond in the form of "STORY: [topic: [user's topic], theme: [user's theme]]". 
                - Topic should not be a simple phrase like "a man smoking".
                - Theme should not be the same as the topic.
                - Don't output any other text.

                ELSE if the user cannot provide either topic or theme:
                - Respond with "Original input: [user's input]". Nothing else.
                - Don't output any other text.
                """,
    output_key=STATE_CURRENT_TOPIC,
    before_model_callback=topic_collection
)

# STEP 0b: Topic Confirmation Agent
topic_confirm_agent = LlmAgent(
    name="TopicConfirmationAgent",
    model=LLM_MODEL,
    include_contents='none',
    instruction=f"""You are an assistant helping the user to confirm topic and theme for a flash story.
                Look at the requirement below to see if either topic or theme is missing.
                Requirement: ```{{current_topic}}```

                IF the requirement is in the form of "STORY: [topic: [user's topic], theme: [user's theme]]",
                - Call the 'exit_sequence' function with the requirement as the argument. Do not output any text.
                - If the requirement is not in the required format, don't call the function, since it means the requirement is missing either topic or theme.

                ELSE if either topic or theme is missing in the requirement, or if the requirement is not in the required format:
                - Just respond with "need additional information." Nothing else.
                """,
    tools=[exit_sequence],
    after_model_callback=topic_clarification,
)

# STEP 0: Loop agent to control the interaction with topic collector agent
topic_collector_loop = LoopAgent(
    name="TopicCollectorLoop",
    sub_agents=[
        topic_collector_agent,
        topic_confirm_agent,
    ],
    max_iterations=5 # Limit loops
)


# STEP 1: Initial Writer Agent (Runs ONCE at the beginning)
initial_writer_agent = LlmAgent(
    name="InitialWriterAgent",
    model=LLM_MODEL,
    include_contents= 'none',
    instruction=f"""You are a Creative Writing Assistant tasked with starting a flash short story.
    Write the *first draft* of a short story (aim for 3-6 sentences) based only on the topic below.
    
    Topic: ```{{current_topic}}```

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
        topic_collector_loop, # Run first to collect topic and theme
        initial_writer_agent, # Run second to create initial doc
        story_refinement_loop       # Then run the critique/refine loop
    ],
    description="Writes an initial document and then iteratively refines it with critique using an exit tool."
)


root_agent = story_writing_pipeline
