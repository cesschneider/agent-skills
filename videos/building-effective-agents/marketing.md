# Marketing Copy — "How Anthropic Builds Effective AI Agents"

Source: [How We Build Effective Agents — Barry Zhang, Anthropic](https://youtu.be/D7_ipDqhtwk) (AI Engineer Summit 2025, New York)

Carousel theme: "Claude brand" (cream/navy/terracotta, `carousel/01.png`–`10.png`).
Narration video rendered via HeyGen (`video_id: c164b7cb74e04c0aad7d5604d96aa649`, duration 7:10). Chapter timestamps below are proportional to that runtime.

## YouTube

**Title:**
```
How Anthropic Builds Effective AI Agents — Barry Zhang's Framework Explained
```

**Description:**
```
Everyone's racing to build "AI agents" right now — but a lot of teams probably shouldn't be. In this video, I break down a talk by Barry Zhang from Anthropic's Applied AI team, who's helped dozens of companies build agentic systems. His framework comes down to three rules: don't build agents for everything, keep it simple, and think like your agents.

We cover the real difference between a "workflow" and an "agent," a simple checklist for deciding which one your problem needs, why coding turned out to be close to the perfect agent use case, the three building blocks every agent needs (environment, tools, and system prompt), and the token-budget constraint that quietly shapes almost every agent design decision.

Chapters:
0:00 Hook — 3 rules for building agents
0:54 Agents vs. Workflows
1:49 Don't build agents for everything (the checklist)
2:47 Coding: the ideal agent use case
3:42 The three building blocks
4:34 Think like your agent (token scarcity)
5:29 Keep it simple, then look ahead
6:23 Your next step

If you're building anything agent-shaped right now, try the exercise at the end of this video — and let me know in the comments what's the biggest bottleneck in your own agent: tools, prompt, or environment?

Source talk: https://youtu.be/D7_ipDqhtwk — "How We Build Effective Agents," Barry Zhang, Anthropic (AI Engineer Summit). [Insert your own video link here once published.]

#AIAgents #Anthropic #AIEngineering #LLM #SoftwareEngineering #AgenticAI #PromptEngineering #BuildInPublic
```

## LinkedIn Post

```
Most teams building "AI agents" right now probably shouldn't be.

That's the blunt starting point of a talk by Barry Zhang from Anthropic's Applied AI team — whose job is literally helping companies build agentic systems. His framework boils down to three rules: don't build agents for everything, keep it simple, and think like your agents.

A few things that stuck with me:

→ Workflows vs. agents isn't a maturity ladder. A workflow is a predefined sequence of model calls; an agent runs in a loop, deciding its own next step from environment feedback. Neither is "better" — they fit different problems.

→ Before reaching for an agent, ask three questions: Is this genuinely ambiguous (can't enumerate the steps)? Is the value worth the exploration cost? What does it cost when the agent gets it wrong? Predictable + budget-constrained = workflow. Ambiguous + high-value = agent territory.

→ Coding is close to the ideal agent use case — it's complex, valuable, the tools already exist (shell, compiler, search), and the output is verifiable with tests. That's a hard combination to beat.

→ Every agent needs three things: an environment, tools (action + feedback), and a system prompt. Weak link in any one of those, and the whole agent struggles.

→ The constraint that changes everything: your agent often has only 10-20K usable tokens of context per step. "Think like your agent" — could YOU complete the task with exactly that context?

Full breakdown in the carousel below 👉

What's the biggest bottleneck in your own agent setup right now — tools, prompt, or environment? Curious what others are running into.

#AIAgents #Anthropic #AgenticAI #SoftwareArchitecture #AIEngineering #LLM #PromptEngineering
```

## Instagram Caption

```
Most teams don't need an AI agent. (Yes, really.) 🤖

Swipe for Anthropic's 3 rules for building agents that actually work — straight from their Applied AI team, who've shipped this stuff with dozens of companies.

The big idea: agents aren't "smarter workflows." They're a different tool for a different kind of problem — and using one when you don't need it just makes things slower, pricier, and harder to debug.

The one that hit hardest: your agent often only "sees" 10-20K tokens of context per step. Think like your agent — could YOU solve the task with just that?

💬 What's the biggest bottleneck in YOUR agent — tools, prompt, or environment? Tell us below.

#AIAgents #Anthropic #AgenticAI #AITools #BuildInPublic #SoftwareEngineering #FutureOfCoding #Claude
```

---

**Note:** All copy above is an original synthesis of the talk's ideas, not a transcript. For the full talk, see the source link above.
