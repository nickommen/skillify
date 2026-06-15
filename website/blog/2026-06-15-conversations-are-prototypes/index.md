---
title: "Skillify: Conversations Are Prototypes, Skills Are Artifacts"
authors: [nickommen]
tags: [skillify, claude-code, automation, workflows]
---

I manage engineering teams, but my day-to-day work is not writing production code. Most of my time is spent on the operational work that sits between engineering, planning, and execution: gathering information from multiple systems, understanding where projects are getting stuck, identifying work that needs attention, and assembling that information into something useful for me and the team.

This year I challenged myself to adopt AI tools into my daily workflow to tackle these manual tasks. Having a conversation with tools like Claude Code was particularly effective because it allows me to start with an outcome rather than an implementation. I can describe what I want, iterate on the results, refine queries, handle edge cases as they appear, and gradually converge on something that solves the problem. The process is often faster than building a dedicated tool, especially when the workflow is still evolving.

{/* truncate */}

The limitation becomes apparent when I need to repeat the same task. Even when a workflow has already been worked out, the model approaches it as a fresh problem. It re-plans the steps, re-discovers the tools involved, and may choose a different implementation path than it used previously. Although the final answer is often acceptable, the reasoning process is repeated from scratch and the knowledge gained during the original conversation remains trapped in the transcript rather than becoming part of a reusable workflow.

After working this way for several months, I realized that I was treating conversations and workflows as if they were the same thing. In practice, they serve very different purposes. Conversations are excellent environments for exploration. They allow requirements to evolve, assumptions to be challenged, and workflows to emerge through iteration. Once a workflow stabilizes, however, the conversation itself becomes a poor place to store it. The transcript contains the successful solution, but it also contains the dead ends, debugging sessions, abandoned ideas, and intermediate corrections that were useful during discovery but add little value during execution.

## Deterministic Core, Agentic Edge

As I thought about these workflows, I found it useful to think of them as progressing through several levels of maturity. Conversations are ideal for discovery because requirements are still changing. Prompt-based skills improve repeatability by capturing instructions in a reusable form. As workflows become more involved, however, deterministic behavior such as calculations, validation rules, and data transformations often end up encoded in prompts and reinterpreted on every execution. Moving those behaviors into executable artifacts improves consistency without requiring the complexity of a full agent architecture.

| **Approach** | **Primary Artifact** | **Effort** | **Consistency** |
| --- | --- | --- | --- |
| Conversation | Transcript | Low | Low-Medium |
| Prompt-based Skill | `SKILL.md` | Low-Medium | Medium |
| Workflow Skill | `SKILL.md` + Scripts | Medium | Medium-High |
| Production Agent | Workflow system | High | High |

The simplest form is a conversation. Everything lives in the transcript. This is ideal for discovery because requirements are still changing, but it also means the workflow must be rediscovered each time it is needed.

The next step is a prompt-based skill. Claude Code Skills already provide a useful mechanism for capturing instructions in a reusable form. For many workflows, a well-written SKILL.md file is enough. The workflow becomes more repeatable because the model starts from documented guidance rather than conversational history.

A workflow skill sits one step further along that spectrum. The workflow still uses a SKILL.md file as the orchestration layer, but deterministic behavior is extracted into scripts and supporting artifacts where appropriate. Instead of describing how to perform a calculation, the skill can execute the calculation directly. Instead of explaining validation rules in natural language, it can run a validator. The model still participates in execution, but it spends less effort reconstructing behavior that has already been defined.

At the far end of the spectrum are production agent systems with explicit state management, workflow orchestration, deployment pipelines, monitoring, and operational controls. Those systems provide the highest degree of consistency and autonomy, but they also require substantially more engineering investment than my smaller, management-focused tasks justify.

What I wanted was something between a prompt and an agent: a way to quickly preserve the outcome of a successful conversation with minimal effort and without turning every workflow into a project.

That idea eventually became [Skillify](https://github.com/nickommen/skillify).

## From Conversation to Skill

The workflow begins with a normal Claude Code session. As an example, I might ask for a weekly report summarizing my team's work over the previous several days. The first result is rarely what I ultimately need. Jira queries get refined, output formats change, edge cases appear, and new requirements emerge as I see the data. It is not unusual to realize midway through the conversation that the report would be more useful if it also included GitHub pull requests or highlighted a specific category of work. During this phase, the model is actively participating in the discovery process because the workflow itself is still being designed.

Eventually the conversation reaches a point where the workflow stops changing. The queries stabilize, the output format settles into something useful, and the corrections become increasingly minor. At that stage, continuing to run the workflow through a conversation feels inefficient because the work being performed is no longer discovery. The workflow has already been discovered.

When I run `/skillify this`, the conversation is treated as source material rather than as the workflow itself. Skillify parses the transcript, extracts tool usage patterns, identifies transformations and output structures, and looks for places where the model was corrected or redirected. Early versions attempted to do this entirely through automated analysis, but transcripts turned out to be much noisier than I expected. A successful conversation contains a mixture of useful decisions and irrelevant exploration, and distinguishing between the two is difficult without additional context.

The solution was to introduce a structured interview step. Rather than assuming the transcript contains everything necessary, Skillify asks a small set of questions about the workflow based on the workflow's complexity. Some of the most important information never appears explicitly in the conversation itself: whether the workflow is safe to run repeatedly, which failures should stop execution, what assumptions must be true before the workflow starts, and what level of autonomy is appropriate.

In some ways this resembles specification-driven development, but in reverse. Traditional specification-driven approaches begin with a specification and produce an implementation. Skillify starts with a working workflow discovered through exploration and extracts the knowledge needed to make it repeatable. The interview is less about defining requirements from scratch and more about formalizing knowledge that emerged during exploration.

## Generating and Running Skills

From there, a generation agent produces the artifacts that make up the skill. In simple cases this may be nothing more than a SKILL.md file. In more complex cases, the generated skill includes supporting Python scripts for validation, data transformation, and report generation. The exact structure depends on the workflow, but the objective remains the same: move deterministic behavior out of the conversation and into reusable artifacts.

The difference becomes most noticeable when the generated skill is executed repeatedly. In my previous weekly report example, the discovery conversation consumed approximately 16k tokens and the skill generation through Skillify consumed an additional 10k tokens. Once created, the workflow executes in roughly 8k tokens per run.

The reduction in token usage and cost is impactful, but the larger benefit is consistency. Once the workflow has been formalized, execution becomes predictable and the output remains stable even as the underlying data changes.

The generated skills are not perfect on the first attempt. This is expected because Skillify's analysis and generation phases are themselves reasoning-driven workflows. The conversation is interpreted, patterns are extracted, and implementation decisions are made by a model. Two agents given the same transcript may produce different skills, just as two conversations can arrive at different solutions.

That variability is part of what motivated the Skillify project in the first place. The goal is not to eliminate reasoning during workflow creation, but to progressively reduce the amount of reasoning required during workflow execution. There are usually adjustments to make, whether that means refining a date calculation, handling a new edge case, or improving the presentation of the results. What changes is the nature of the work. Instead of repeatedly rediscovering a workflow through conversation, I am refining a concrete artifact. Corrections accumulate over time and become part of the skill itself, making future executions more reliable.

## What Changed For Me

The most significant change for me has been a shift in how I think about AI-assisted work. Conversations remain the best place for me to explore ideas, experiment with approaches, and discover workflows. Prompt-based skills provide a useful way to preserve those workflows. Workflow skills go a step further by moving deterministic behavior into executable artifacts while still allowing the model to orchestrate execution. Most of the workflows I rely on do not need to become agents, but they can benefit from the consistency and efficiency provided by workflow skills.

Skillify emerged from that realization. Rather than viewing conversations as the final product, I now treat them as the place where workflows are discovered. Once a workflow stabilizes, preserving it as an artifact allows the model to focus its reasoning where it provides the most value while allowing the predictable parts of the process to remain predictable.

The conversation creates the workflow. The skill preserves it.

Skillify is open source at [github.com/nickommen/skillify](https://github.com/nickommen/skillify).
