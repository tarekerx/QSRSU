# I will write here my journey of solving prompts — what I faced, what I learned, and why I built it. I write all of it myself of course; I'm just using a text enhancer. The organic content is from me.**


# Day Log — November 26, 2026, 6:45 PM

## What I built today

Today I want to write down where my current project actually started from, because the problem is older than the project itself.

My problem started 2 years ago, when I started studying for exams like the SAT and ACT, where you have to solve sheets with a lot of questions. Of course I got some wrong, so I was screenshotting them and sending them to myself to review later. But this had a lot of drawbacks:

- no nice way of tracking which question is tricky and which one I got wrong just for not focusing
- I had to search for the answer for every question again, which was annoying

So I thought: why not make something like a website for that?

I have an **Ubuntu server on an old laptop** that I would run the server on, and use the website from there. The loop I thought of looks like this:

1. Send the question (screenshot) via a **Telegram bot**, handled by a **Python** script
2. Pass it to a **local LLM** for describing the image and the things in it
3. Then pass it to the **big LLM via an API key** for solving it — because this step needs some intelligence, unlike the description step
4. Store everything in a **SQLite** database for easy handling — and I'm not running a company now, so no need for PostgreSQL
5. The loop repeats

And of course it is not as simple as I'm saying. A lot of problems will be faced — which is exactly what I started this for: to face problems, document them, learn from them, and improve in my academic life and developer life.

## What I learned

This was mostly a planning day, but one thing became clear while thinking the architecture through: **match the tool to the job, not to the hype**. The describing step doesn't need a smart model — a local LLM on my own hardware is enough and costs nothing. The solving step is where the real reasoning is needed, and that's the only place worth spending an API key. Splitting the pipeline this way keeps the expensive part small.

> Don't give every step the biggest model. Give each step the smallest model that can actually do it.

---

*One small note: SQLite is a great choice here — but just so the reasoning is straight in your head, the "no company, so SQLite" logic is about scale and simplicity, not about SQLite being a lesser database. It will handle this project perfectly.*
