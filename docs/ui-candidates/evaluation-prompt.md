# Punkto UI Candidate — Independent Evaluation Prompt

Use this prompt when asking an AI or human reviewer to evaluate the Punkto interface candidates.

---

## Reviewer task

You are evaluating high-level UI and product-design candidates for **Punkto**, a public geospatial bulletin-board system.

Punkto consists of public messages called atoms or Punkti, anchored to exact real-world locations and optionally altitude. A root atom may have public replies or notes attached to it. The message and place are primary; the author is secondary. Punkto currently has no requirement for private messaging, followers, popularity mechanics, or a conventional profile-driven social graph.

Review the candidate independently. Do not merely praise the mockup. Do not propose code unless specifically asked.

## Shared product goals

The interface should be:

- understandable to ordinary non-technical users
- warm, calm, social, and slightly game-like
- visually distinctive enough to become Punkto's identity
- useful for everyday messages, infrastructure information, and urgent local reports
- respectful of the uniqueness and exact position of every atom
- feasible on ordinary mobile hardware, preferably as a PWA
- scalable from sparse early use to dense city and global activity

## Required scenarios

Consider how the candidate handles:

1. **Everyday social:** “Bench by the canal has sun until 7 pm.”
2. **Infrastructure thread:** “Fire hydrant not working.” Reply: “I confirm, it has not been working for a week. County is informed.”
3. **Urgent report:** “Flooding here — road blocked.”

## Evaluation questions

### 1. Five-second comprehension

What would a first-time user believe Punkto is after five seconds?

### 2. Strongest idea

What is the most valuable and ownable idea in this candidate?

### 3. Largest failure risk

What is most likely to confuse users, damage social acceptance, or make the design impractical?

### 4. Message and place hierarchy

Does the design make the message and its location more important than generic interface chrome or author profiles?

### 5. Atom and thread clarity

Can the viewer distinguish:

- one independent atom
- a root atom with replies
- multiple nearby independent atoms
- an active or newly updated thread

### 6. Scale behavior

How well can the candidate work at:

- world
- city
- neighborhood
- exact atom/thread

### 7. Social character

Does it feel warm and human without becoming a conventional social-media clone?

### 8. Engineering realism

What are the likely mobile rendering, data, asset, interaction, or implementation risks?

### 9. Sparse-world behavior

Would it still feel intentional and useful when there are only a few messages nearby?

### 10. Recommendation

Choose one:

- **KEEP** — strong enough to remain a full candidate
- **REVISE** — valuable direction but needs substantial correction
- **COMBINE** — best used as part of another candidate
- **REJECT** — insufficient product value or impractical risk

## Scores

Score each dimension from 1 to 5 and briefly justify each score.

| Dimension | Score | Reason |
|---|---:|---|
| Clarity | /5 | |
| Desirability | /5 | |
| Punkto uniqueness | /5 | |
| Social warmth | /5 | |
| Practical usefulness | /5 | |
| Atom/thread clarity | /5 | |
| Mobile feasibility | /5 | |
| Scalability | /5 | |

## Final response format

1. One-paragraph verdict
2. Scores table
3. Strongest idea
4. Largest failure risk
5. Three specific improvements
6. KEEP / REVISE / COMBINE / REJECT
7. Comparison with the other candidates, if available

## Review storage

Save reviews using the reviewer name under the relevant candidate folder, for example:

```text
candidate-1/reviews/claude.md
candidate-2/reviews/gemini.md
candidate-3/reviews/chatgpt.md
```

Keep observations evidence-based and separate current facts from design speculation.
