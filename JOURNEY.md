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


# Day Log — November 26, 2026, 11:45 PM

## What I built today

I started my new project, **QSRSU**. First prompt I gave to my coding agent — of course not writing the code by my hand, but understanding every line of it. This is the prompt I gave him:

> We are in a project called QSRSU. Structure: `bot/main.py` (entry point), `bot/handlers.py` (message handlers), `bot/config.py` (loads `.env`), `.env` (`TELEGRAM_BOT_TOKEN`), `requirements.txt`. Use python-telegram-bot v21+ with async handlers. The bot echoes any text message back. Add a `.gitignore` for `.env`, `__pycache__`, `images/`.

And then I told him:

> Add a virtual environment (`venv`), activate it, and install the dependencies.

## What I learned

I hovered over what he did and stopped at every unknown concept until I understood it. Some of the ones I locked in today:

- **The `Update` object** — this is the incoming message payload. It's what came from the user: the text, who sent it, whether it's a new message or an edit.
- **The `Context` object** — different kind of data. Also given to the handler, but it's runtime stuff, not the user's message: the bot instance, the application.
- **`async` / `await`** — this one took me a second. If we mark the function `async`, it means the function can pause and wait. But here's the part that clicked: the pause only happens at `await`. So in our case, when we hit `await reply_text(...)`, our function waits for Telegram's response — and meanwhile, other operations continue without being interrupted. The bot doesn't freeze; it just parks that one handler until the network answers.

So the full picture: `update` = what happened, `context` = what I can do about it. And `async` without `await` is just a promise — nothing actually pauses until you use it.


---
