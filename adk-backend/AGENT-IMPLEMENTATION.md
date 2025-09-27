# Autonomous Robot Control: A Conceptual Agent Architecture

## Overview

This document outlines the conceptual design for an autonomous robot control system built using a team of specialized agents. The architecture emphasizes a clear separation of concerns, from high-level strategic planning to real-time execution, all coordinated through a shared memory space. This agent-first approach allows for complex, multi-step tasks to be broken down and managed effectively.

## System Architecture

The system is composed of a team of agents, each with a specific role, working in a coordinated fashion. The flow of information and control is designed to handle complex goals through distinct planning and execution phases.

```mermaid
graph TD
    subgraph "Overall System"
        direction LR
        A[User Goal] --> RA[Director<br/>(Root Agent)]

        subgraph "Phase 1: Planning"
            direction TB
            RA --> PA[Strategist<br/>(Planner Agent)]
            PA --> SM[Shared Plan]
        end

        subgraph "Phase 2: Execution Loop"
            direction TB
            SM --> GE[Mission Controller<br/>(Goal Evaluator)]
            GE -- Assesses Progress --> PC[Operations Manager<br/>(Plan Coordinator)]

            subgraph "Concurrent Operations"
                direction LR
                PC -- Dispatches Tasks --> MA[Pilot<br/>(Motor Agent)]
                PC -- Dispatches Tasks --> VA[Observer<br/>(Vision Agent)]
            end
        end
    end

    subgraph "External Systems"
        direction TB
        MA --> HW[Robot Hardware API]
        VA --> VS[Vision System API]
    end

    SM -- Is Stored In --> SMS[Shared Memory Space]
    GE -- Reads From --> SMS
    PC -- Reads/Writes To --> SMS
    MA -- Reads/Writes To --> SMS
    VA -- Reads/Writes To --> SMS
```

## The Agent Team

Our robot's intelligence is distributed across a team of collaborating agents:

-   **The Director (Root Agent)**: The entry point of the system. It receives the high-level goal from the user, establishes the shared memory space for the mission, and passes the objective to the planning phase.

-   **The Strategist (Planner Agent)**: This agent acts as the master planner. It takes the user's goal and breaks it down into a detailed, sequential plan of atomic steps. It considers the robot's capabilities and the nature of the task to create a comprehensive roadmap, which it then stores in the shared memory.

-   **The Mission Controller (Goal Evaluation Agent)**: Operating at the highest level of the execution loop, this agent continuously assesses progress against the original goal. It determines if the mission is on track, successfully completed, or has failed, guiding the overall execution loop.

-   **The Operations Manager (Plan Coordinator Agent)**: The tactical leader of the execution phase. It reads the shared plan and, for each cycle of the loop, identifies the next step to be executed. It then dispatches the specific tasks to the appropriate agents (Pilot, Observer).

-   **The Pilot (Motor Agent)**: This agent is responsible for the robot's physical movement. It executes low-level commands based on the current step provided by the Operations Manager, such as moving forward or rotating. It is aware of its environment by reading data from the shared memory provided by the Observer.

-   **The Observer (Vision Agent)**: The eyes of the operation. This agent processes the camera feed via the vision system to identify objects, obstacles, and targets. It populates the shared memory with its findings, providing crucial environmental context for the other agents, especially the Pilot.

## The Orchestration Flow

The agents work together in a structured workflow orchestrated by ADK's workflow agents.

1.  **Phase 1: Planning (`SequentialAgent`)**
    The process starts sequentially. The **Director** receives the goal, then hands off to the **Strategist** to create a complete plan. This ensures a solid plan is in place before any action is taken.

2.  **Phase 2: Execution (`LoopAgent`)**
    Once the plan is ready, the system enters a continuous execution loop. In each cycle:

    -   The **Mission Controller** evaluates if the main goal is complete.
    -   If not, the **Operations Manager** selects the next task from the plan.
    -   The task is then executed through concurrent operations.
        This loop continues until the mission is marked as complete or has failed.

3.  **Concurrent Operations (`ParallelAgent`)**
    Within each loop cycle, the **Pilot** and the **Observer** work in parallel. The robot can move and see at the same time, allowing for dynamic and responsive behavior as it navigates its environment.

## The Shared Mind (Shared Memory)

Coordination is achieved through a "Shared Memory Space" (the ADK Session State). This is a central repository where the mission-critical information is stored and accessed by all agents. Key pieces of information include:

-   **The Goal**: The original user-defined objective.
-   **The Plan**: The detailed, step-by-step plan created by the Strategist. Each step has a status (e.g., pending, in_progress, completed).
-   **Observations**: Real-time information from the Observer about what the robot sees.
-   **Mission Status**: The overall status of the mission (e.g., planning, executing, complete).

This shared context ensures every agent has the information it needs to perform its role effectively and stay synchronized with the rest of the team.

## Available Capabilities (Tools)

The agents have access to a set of natural language tools to interact with the robot and its vision system:

-   **Movement**: `move_forward`, `move_backward`, `rotate`, `stop_robot`, `scan_environment`
-   **Vision**: `view_query` (to search for specific objects), `clarify_view_with_gemini` (to ask complex questions about the scene)

---

## Relevant ADK Samples for Further Development

To aid in the implementation of this architecture, the following samples from the ADK repository provide valuable patterns and examples that align with our proposed design:

### 1. Academic Research (`python/agents/academic-research`)

This sample demonstrates a powerful "coordinator" agent pattern.

-   **Why it's relevant**: It features a main `academic_coordinator` agent that orchestrates the workflow by calling specialized sub-agents (`academic_websearch_agent`, `academic_newresearch_agent`) as tools. This directly maps to our architecture where the `Plan Coordinator` would dispatch tasks to agents like the `Motor Agent` and `Vision Agent`. It's a great example of how to structure a team of collaborating agents.

### 2. Blog Writer (`python/agents/blog-writer`)

This sample provides a clear example of a structured, multi-step workflow with human-in-the-loop interaction.

-   **Why it's relevant**: The main `interactive_blogger_agent` follows a defined sequence: Plan -> Refine -> Write -> Edit -> Promote. It delegates each phase to a specific sub-agent (e.g., `robust_blog_planner`, `robust_blog_writer`). This is very similar to our proposed Planning Phase followed by an Execution Loop. It showcases how to build a complex, stateful workflow where the output of one step becomes the input for the next.

### 3. Incident Management (`python/agents/incident-management`)

While simpler, this example is a good starting point for understanding how to wrap external APIs as tools for an agent.

-   **Why it's relevant**: It contains a single agent that uses a `snow_connector_tool` to interact with the ServiceNow API. This provides a direct parallel to how our `Motor Agent` will use tools to interact with the JetBot Hardware API. It is a clean, focused example of tool-based integration.
