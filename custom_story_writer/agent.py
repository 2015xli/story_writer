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
APP_NAME = "story_writing_agent" # New App Name
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

# --- Custom Orchestrator Agent ---
class VibeWritingAgent(BaseAgent):
    """
    Custom agent for a story generation and refinement workflow.
    I use custom agent because I need the first agent to interact with the user to collect topic and theme.
    """

    # --- Field Declarations for Pydantic ---
    # Declare the agents passed during initialization as class attributes with type hints
    topic_collector_agent: LlmAgent
    initial_writer_agent: LlmAgent
    critic_agent_in_loop: LlmAgent
    refiner_agent_in_loop: LlmAgent

    story_refinement_loop: LoopAgent
    story_writing_pipeline: SequentialAgent

    # model_config allows setting Pydantic configurations if needed, e.g., arbitrary_types_allowed
    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        topic_collector_agent: LlmAgent,
        initial_writer_agent: LlmAgent,
        critic_agent_in_loop: LlmAgent,
        refiner_agent_in_loop: LlmAgent
    ):
        """
        Initializes the VibeWritingAgent.

        Args:
            name: The name of the agent.
            topic_collector_agent: An LlmAgent to collect topic and theme.
            initial_writer_agent: An LlmAgent to generate the initial story.
            critic_agent_in_loop: An LlmAgent to critique the story.
            refiner_agent_in_loop: An LlmAgent to refine the story.
        """
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
        # Define the sub_agents list for the framework
        sub_agents_list = [
            topic_collector_agent,
            story_writing_pipeline,
        ]

        # STEP 4: Initialize the root agent
        # Pydantic will validate and assign them based on the class annotations.
        super().__init__(
            name=name,
            topic_collector_agent=topic_collector_agent,
            initial_writer_agent=initial_writer_agent,
            critic_agent_in_loop=critic_agent_in_loop,
            refiner_agent_in_loop=refiner_agent_in_loop,
            story_refinement_loop=story_refinement_loop,
            story_writing_pipeline=story_writing_pipeline,
            sub_agents=sub_agents_list, # Pass the sub_agents list directly
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Implements the custom orchestration logic for the vibe story writing workflow.
        Uses the instance attributes assigned by Pydantic (e.g., self.story_generator).
        """
        logger.info(f"[{self.name}] Starting story generation workflow.")
        ctx.session.state["init_topic"] = ""
 
        # 1. Initial Story topic collection
        logger.info(f"[{self.name}] Running TopicCollectorAgent...")
        while True:
            async for event in self.topic_collector_agent.run_async(ctx):
                logger.info(f"[{self.name}] Event from TopicCollectorAgent: {event.model_dump_json(indent=2, exclude_none=True)}")
                yield event

            # Check if story was generated before proceeding
            topic = ctx.session.state.get("current_topic", "")
            if topic == "":
                logger.error(f"[{self.name}] Failed to generate initial story. Aborting workflow.")
                return # Stop processing if initial story failed
            elif topic.startswith("STORY:"):
                logger.info(f"[{self.name}] Topic collected: {topic}")
                break
            else:
                logger.info(f"[{self.name}] Topic collection not complete. Retrying...")
                print("[user]:", end="")
                user_input = input()
                ctx.session.state["init_topic"] = ctx.session.state["init_topic"] + "\n and: " + user_input                

        logger.info(f"[{self.name}] Story state after topic collection: {ctx.session.state.get('current_topic')}")


        # 2. Story Writing Pipeline (includes initial writer and refinement loop)
        logger.info(f"[{self.name}] Generating story and refining in loop...")
        async for event in self.story_writing_pipeline.run_async(ctx):
            logger.info(f"[{self.name}] Event from StoryWritingPipeline: {event.model_dump_json(indent=2, exclude_none=True)}")
            yield event

        logger.info(f"[{self.name}] Story state after loop: {ctx.session.state.get('current_document')}")

        logger.info(f"[{self.name}] Workflow finished.")

# STEP 0: Topic Collector Agent
topic_collector_agent = LlmAgent(
    name="TopicCollectorAgent",
    model=LLM_MODEL,
    include_contents='default',
    instruction=f"""You are collecting topic and theme for a story.
                Look at the conversation history and "{{init_topic}}" to extract topic and theme.
                Example topics: a person who wants to save the city with his friends, a programmer was rejected by his girlfriend.
                Example themes: fantasy, science fiction, horror, romance, comedy, drama, thriller, mystery, young adult, middle grade.

                IF you can identify BOTH a clear topic and valid theme from the conversation:
                - You must respond with "STORY: [topic: [user's topic], theme: [user's theme]]". 
                - Topic and theme cannot be the same. If they are the same, you must ask for a different topic or theme.
                - Do not output any additional text.

                ELSE if either topic or theme is missing:
                - Ask specifically for the missing parts (topic or theme or both).
                """,
    output_key=STATE_CURRENT_TOPIC,
)

# STEP 1: Initial Writer Agent (Runs ONCE at the beginning)
initial_writer_agent = LlmAgent(
    name="InitialWriterAgent",
    model=LLM_MODEL,
    include_contents= 'none',
    instruction=f"""You are a Creative Writing Assistant tasked with starting a flash short story.
    Write the *first draft* of a short story (aim for 3-6 sentences) based only on the topic and theme below.
    Try to introduce a specific element (like a character, a setting detail, or a starting action) to make it engaging.
    Output *only* the story document text. Do not add introductions or explanations.
    
    Topic and Theme: ```{{current_topic}}```

    Make sure the story is interesting and engaging.
    """,
    description="Writes the initial document draft based on the topic, aiming for some initial substance.",
    output_key=STATE_CURRENT_DOC
)

# STEP 2a: Critic Agent (Inside the Refinement Loop)
critic_agent_in_loop = LlmAgent(
    name="CriticAgent",
    model=LLM_MODEL,
    include_contents='none',
    instruction=f"""You are a Constructive Critic AI reviewing a short story draft (typically 3-6 sentences) for a flash story. Your goal is to help the writer improve the story.

    **Topic and Theme:**
    ```{{current_topic}}```

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

root_agent = VibeWritingAgent(
    name="VibeWritingAgent",
    topic_collector_agent=topic_collector_agent,
    initial_writer_agent=initial_writer_agent,
    critic_agent_in_loop=critic_agent_in_loop,
    refiner_agent_in_loop=refiner_agent_in_loop,
)
    