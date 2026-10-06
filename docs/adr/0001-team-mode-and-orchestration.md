# ADR 0001: Agno Team Mode and Workflow Orchestration Architecture

## Status
Accepted

## Context
RivalScope requires orchestrating multiple specialized agents to perform competitive intelligence monitoring, claim verification, fintech synthesis, and multi-channel report generation.

Agno 3.1 provides two primary paradigms for multi-agent coordination:
1. **Agno Teams (`agno.team.Team`)**: Groups of agents with a leader coordinating members under specific modes (`TeamMode.coordinate`, `TeamMode.route`, `TeamMode.broadcast`, `TeamMode.tasks`).
2. **Agno Workflows (`agno.workflow.Workflow`)**: Deterministic pipelines supporting sequential, conditional, looped, and parallel step execution (`Parallel`, `Steps`, `Condition`, `Router`).

We need to decide whether to use `TeamMode.coordinate`, `TeamMode.broadcast`, or a hybrid combination with Agno Workflows for batch collection and interactive analysis.

## Decision
We adopt a **hybrid orchestration model**:
1. **Batch Scheduled Pipeline -> Agno Workflow (`MonitorPipelineWorkflow`) with `Parallel` collectors**:
   - The scheduled monitoring pipeline follows a structured, repeatable Directed Acyclic Graph (DAG):
     `Parallel(NewsScout, ProductWatcher, FinanceAnalyst, TalentSignals, SocialPulse) -> normalize -> dedup -> persist -> VerifierAgent -> AnalystAgent -> ReporterAgent -> deliver`.
   - Workflows provide deterministic error isolation, granular step-by-step progress events for UI streaming, and access to all prior outputs via `StepInput`.
   - Using `TeamMode.broadcast` for collection in a team was considered, but in broadcast mode the team leader sends the identical prompt to all members simultaneously and synthesizes the outputs in a single LLM call. This is inefficient for collectors that each require specialized inputs (e.g. SEC ticker vs blog URL) and produce structured documents rather than conversational answers.

2. **Interactive On-Demand Intelligence -> Agno Team (`TeamMode.coordinate`)**:
   - For on-demand user queries ("Compare competitor X's pricing strategy against our new tier"), we use `Team(members=[VerifierAgent, AnalystAgent, ReporterAgent], mode=TeamMode.coordinate)`.
   - The coordinator acts as the lead fintech research director. It analyzes user queries, delegates sub-tasks to the verifier or analyst as needed, and synthesizes cited answers.
   - `TeamMode.coordinate` preserves member separation and enables multi-turn conversation memory with `add_team_history_to_members`.

## Consequences
- **Positive**: High reliability, deterministic pipeline execution during automated crawls, cost control (cheap models for parallel collectors, reasoning model for analyst), clear UI progress reporting.
- **Negative**: Requires maintaining two execution entry points (`Workflow` for scheduled batch monitoring and `Team` for chat/deep-dive investigations).
