# My Journey Solving Prompts

I will write here my journey of solving prompts — what I faced, what I learned, and why I built it. I write all of it myself of course; I'm just using a text enhancer. The organic content is from me.

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

_One small note: SQLite is a great choice here — but just so the reasoning is straight in your head, the "no company, so SQLite" logic is about scale and simplicity, not about SQLite being a lesser database. It will handle this project perfectly._

---

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

# Day Log — November 27, 2026

## What I built today

Added a SQLite database layer to my QSRSU project (Telegram bot for quiz grading). The prompt I passed:

- Created `db/database.py` using the built-in `sqlite3` module — **no ORM**, deliberately
- Table `questions` with exactly these columns: `id` INTEGER PRIMARY KEY AUTOINCREMENT, `telegram_user_id`, `image_path`, `question_text`, `options` (a JSON string like `{"A": "...", "B": "..."}`), `user_answer`, `correct_answer`, `explanation`, `is_correct` (NULL / 0 / 1), `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- Wrote the functions: `init_db()` (creates the table if it doesn't exist, called once at bot startup), `create_question(telegram_user_id, image_path) -> int`, `update_question(question_id, **fields)`, `get_question(question_id)`, `list_questions()` — all using **parameterized queries only**, never string formatting for SQL values
- Wired `init_db()` into `bot/main.py` so the database is ready **before polling starts**

## What I learned

Honestly — nothing special here. It was not new for me. The point of this step was not the SQL itself, it was **setting the structure deliberately**: plain `sqlite3` + a simple schema is enough for my current state, and later I could change it (upgrade to an ORM, add migrations, whatever) using the same logic without rewriting everything. Small steps, built on purpose.

The `update_question(question_id, **fields)` pattern is also a nice flexible design — it lets me update any column by id without writing five separate update functions.

---

# Day Log — November 27, 2026

## What I built today

Moved to the next phase: making the Telegram bot accept an image, initialize a DB row for it, get the id, then download the image to a local path (not inside the repo directory — locally), and send back a message saying "received, description not here yet". The prompt I passed:

```
Continue the QSRSU project. Add a photo handler to the Telegram bot — still using python-telegram-bot.

In bot/handlers.py (or a new bot/photo_handler.py, your call):
- Register a handler for photos (MessageHandler with Filters.PHOTO or the v20 equivalent)
- When a user sends a photo:
  1. Get the largest photo size's file_id
  2. Create the DB row FIRST: question_id = create_question(telegram_user_id=update.effective_user.id, image_path="") — insert a placeholder empty string for image_path for now
  3. Download the photo via bot.get_file(file_id) and .download_to_drive(), save it to images/<question_id>.jpg (create the images/ directory if it doesn't exist)
  4. Update the row: update_question(question_id, image_path="images/<question_id>.jpg")
  5. Reply to the user: "Photo received (question #<question_id>). Transcription is not wired up yet."
- If downloading or saving fails, delete the DB row you created (keep the DB consistent) and reply with an error message

Config:
- Add IMAGE_DIR = "images" to bot/config.py, loaded from .env if present (IMAGE_DIR), default "images"
- Make sure images/ is added to .gitignore

Important details:
- Use absolute paths via pathlib.Path(__file__) so the images dir is always relative to the project root, not the cwd
- All DB access must go through the existing functions in db/database.py — do not write new SQL here

Keep the code minimal and well-commented — I'm learning and need to understand every part. Add short comments explaining why the DB row is created before the file is saved.
```

## What I learned

I read the whole code and understood it — which is a crucial thing for learning. The changes were small: adding a new handler and some `.gitignore` paths. Then I read the photo handler code line by line. It was very good and I understood everything that was new:

- `get_file(file_id)` → returns a `File` object that has the file id, size, and path (the path is fetched from Telegram's servers in this call — it's not stored locally)
- that object has the method for downloading it
- the download uses `download_to_drive(custom_path=...)` where the custom path is a variable we initialized as a static path at first — of course
- all of that is in `await` because it relies on server responses — the function pauses instead of blocking everything for one thing only
- try/except for handling future errors if there is any

## What went wrong

Nothing broke this time. The only "mistake" risk would have been trusting the model's output without reading it — so I made sure to read everything first.

---

# Day Log — November 27, 2026, 7:30 PM

## What I built today

Now to implement the transcription model — by far the hardest thing I will face in this project. I sent the prompt after some changes because I wanted to use my Ubuntu server for the small transcription model and use OpenVINO to optimize it. The prompt I passed:

````
Continue the QSRSU project. Add an image transcription module using a local vision model — Qwen/Qwen3.5-4B served via OpenVINO GenAI (VLMPipeline, device "CPU"), running on my Ubuntu server. Do NOT use Ollama for this.

Create ai/transcriber.py:
- Function transcribe_question(image_path: str) -> dict | None
- Uses openvino_genai.VLMPipeline, loaded ONCE at module level (or a small loader function with caching — do NOT reload the model on every photo, it takes minutes on CPU)
- Model path and device from bot/config.py: VLM_MODEL_PATH from .env, VLM_DEVICE default "CPU"
- Call the pipeline with the image and a prompt that asks for STRICT JSON only, no markdown fences, no explanation, with exactly these keys:
  {
    "question_text": "<the question text as written>",
    "options": {"A": "...", "B": "..."},
    "user_answer": "<the user's marked answer as a letter, or null if none>"
  }
- Parse the response:
  - Strip any leading/trailing whitespace and possible ```json fences
  - json.loads() the result
  - Validate: question_text must be a non-empty string, options must be a dict of letter->string, user_answer must be a string or None
  - If parsing or validation fails, return None (do NOT raise)
- check_vlm() -> bool that verifies the model directory exists and the pipeline can be constructed; call it once at bot startup in bot/main.py and log a warning if it fails

Wire it into the bot photo flow (bot/photo_handler.py):
- After the image is saved, call transcribe_question(image_path)
- On success: update_question(question_id, question_text=..., options=json.dumps(options), user_answer=...) — store options as a JSON string, remember the column is TEXT
- On failure (None): leave the row as-is and reply to the user: "Couldn't read the question from this photo. Try a clearer image."

Important notes:
- Load the VLMPipeline lazily or at startup, but never per-request — model loading on CPU is slow
- All DB access must go through the existing functions in db/database.py

Keep the code minimal and well-commented — I'm learning and need to understand every part. Add short comments explaining why the JSON is validated instead of trusted directly, why the pipeline is loaded only once, and why options is json.dumps()'ed before storing.
````

## What I learned

**Lazy imports.** I learned something called lazy import — you import a module when you need it inside the function, not at the top. In my case it was `openvino_genai`. The lazy import mattered for two reasons: the bot can import `ai.transcriber` even before `openvino-genai` is installed (which is exactly my current state — I'm installing the libraries right now), and the heavy OpenVINO library is only loaded into memory when transcription is first actually used, not at bot startup. _Correction to what I first thought: it's not really about "importing every time being a waste" — Python caches modules after the first import, so re-importing costs almost nothing. What must not repeat is not the import but the `VLMPipeline(...)` construction — that builds the model's inference graph and takes minutes on CPU, which is why the code keeps the pipeline in a `_pipeline` singleton loaded once and reused for every photo._

**Layered error checking.** I learned that checking for errors or null/None depends on the layer — so checking in every layer is crucial, but each layer is checking a _different_ thing. In `transcribe_question` there are two checks: "is this even valid JSON at all?" and "it's valid JSON, but does it have the right shape (`question_text`, `options` as a dict, etc.)?". Then the caller checks a third time: "did the whole transcription succeed or not?" The caller doesn't care _why_ it failed — blurry photo, bad JSON, wrong shape, missing model — the answer is the same: "ask for a clearer image." Detail at the inner layers, yes/no at the outer one.

## What went wrong

Nothing broke yet — but the model isn't even fully installed on the server at this point, so nothing has really been tested. The first real photo through the VLM is still ahead, and I expect the hardest bugs to show up there.

---

# Day Log — November 27, 2026, 8:30 PM

## What I built today

My quiz-grader bot (Telegram bot → photo → transcription → solve → grade) now has a working transcriber. Sooner than I expected, an error appeared — but it wasn't a real error in my code. It was the **unavailability of installing such a good model for transcribing the images** locally. The local Qwen/Qwen3.5-4B via OpenVINO plan on my Ubuntu server didn't work out.

So I went to plan B: using a free API key like Groq, and using a high-limit model only for description/transcription. And that worked fine.

## What went wrong

- Tried to run the transcription with a local vision model (`Qwen/Qwen3.5-4B` served via `openvino_genai.VLMPipeline`, device `"CPU"`). Getting a model like that installed and usable locally was the blocker — not my code.
- I also ended up with **unwanted libraries installed** from the first attempt at the local model, which I uninstalled afterwards.

The prompt I gave the AI for the local-model attempt was:

````text
Continue the QSRSU project. Add an image transcription module using a local vision model — Qwen/Qwen3.5-4B served via OpenVINO GenAI (VLMPipeline, device "CPU"), running on my Ubuntu server. Do NOT use Ollama for this.

Create ai/transcriber.py:
- Function transcribe_question(image_path: str) -> dict | None
- Uses openvino_genai.VLMPipeline, loaded ONCE at module level (or a small loader function with caching — do NOT reload the model on every photo, it takes minutes on CPU)
- Model path and device from bot/config.py: VLM_MODEL_PATH from .env, VLM_DEVICE default "CPU"
- Call the pipeline with the image and a prompt that asks for STRICT JSON only, no markdown fences, no explanation, with exactly these keys:
  {
    "question_text": "<the question text as written>",
    "options": {"A": "...", "B": "..."},
    "user_answer": "<the user's marked answer as a letter, or null if none>"
  }
- Parse the response:
  - Strip any leading/trailing whitespace and possible ```json fences
  - json.loads() the result
  - Validate: question_text must be a non-empty string, options must be a dict of letter->string, user_answer must be a string or None
  - If parsing or validation fails, return None (do NOT raise)
- check_vlm() -> bool that verifies the model directory exists and the pipeline can be constructed; call it once at bot startup in bot/main.py and log a warning if it fails

Wire it into the bot photo flow (bot/photo_handler.py):
- After the image is saved, call transcribe_question(image_path)
- On success: update_question(question_id, question_text=..., options=json.dumps(options), user_answer=...) — store options as a JSON string, remember the column is TEXT
- On failure (None): leave the row as-is and reply to the user: "Couldn't read the question from this photo. Try a clearer image."

Important notes:
- Load the VLMPipeline lazily or at startup, but never per-request — model loading on CPU is slow
- All DB access must go through the existing functions in db/database.py

Keep the code minimal and well-commented — I'm learning and need to understand every part. Add short comments explaining why the JSON is validated instead of trusted directly, why the pipeline is loaded only once, and why options is json.dumps()'ed before storing.
````

## What I learned

> OpenVINO uses **paths** better, especially when it's local. But for the new case of a cloud LLM, I would use an **API key** for sending requests.

The mental model that finally clicked:

- **Local model** = a folder of weight files on your own disk. There is no server, no account, no one to authenticate against — so the program needs a _path_ to the model files, and the inference library loads them directly.
- **Cloud LLM** = someone else's datacenter doing the work. The API key is how they know it's you and meter your usage. You send the request over HTTP; you never see the weights.

The failed local attempt wasn't wasted time — it taught me exactly when each pattern applies. And when the architecture changed (self-hosted inference → managed inference), the key became the natural way in.

# Day Log — November 27, 2026, 9:10 PM

## What I built today

On to the next phase: the **solver**. Simple approach — add the Gemini API key, request the AI to solve the questions, then update the row of the question to include the explanation and the answer. The answer kept as a little answer, not letters, for the journeys(?), and the response of the AI was standardized.

## What went wrong

When I reviewed the AI's code, I found the row update was **inside `solver.py`** — which at first is only meant to be for solving, not updating. That can catch errors or update hard (a failed or hidden DB write inside the solver makes failures hard to diagnose, and mixing solving with saving makes the function hard to test). So I requested another prompt from my planner, and here it comes — the careful review. The two prompts:

**Prompt 1 — build the solver (phase 4):**

````text
Build phase 4: ai/solver.py — the answering/grading step of the quiz-grader Telegram bot. Do not modify the transcriber or the photo handler's logic.
Context: ai/transcriber.py already extracts {"question_text", "options", "user_answer"} from each quiz photo and saves it to the SQLite questions row. Now the bot must solve the question, grade the student's marked answer, and reply in Telegram.
Requirements:
Create ai/solver.py using Google's google-genai SDK (add GEMINI_API_KEY to .env, loaded in bot/config.py like the other secrets). Model: gemini-2.5-flash. Create the client once at module level, not per request. Verify the key exists at startup; print a clear error and exit if missing.
Function signature: solve_and_grade(question_id: int) -> dict | None — it loads the question row from the DB (reuse the existing get_question() from db/database.py), sends ONLY the text fields (question_text, options) to Gemini — never the image — and asks it to return ONLY a JSON object with this exact schema: {"correct_answer": str, "explanation": str}.
Strict parsing: extract the JSON block (handle a leading ```json fence), json.loads it, validate correct_answer is a non-empty string and explanation is a string. Retry the API call once on parse failure, then return None on second failure.
In Python (not in the prompt), compare correct_answer against the row's user_answer: case-insensitive, ignore surrounding whitespace; set is_correct = True if they match, else False. Handle the case where user_answer is empty (nothing marked) — grade it as incorrect.
Update the DB row with correct_answer, explanation, and is_correct using the existing update_question().
Wire it into the bot flow: after the transcriber successfully fills the row (existing code), call solve_and_grade(question_id), then send the user a Telegram reply in this format:
✅ Correct! (or ❌ Wrong. The correct answer is: X)
Explanation: <explanation>
If solving returned None, reply: "Couldn't solve this one — try a clearer photo." and leave the row unsolved.
Error handling: any API or network failure returns None (same fallback reply). Never crash the handler.
Keep the code minimal and commented — add short comments in ai/solver.py explaining how the google-genai SDK call works and why the model only receives text (the user is learning and needs to understand every part).
````

**Prompt 2 — the refactor after my review:**

```text
Refactor the solver/DB-write split in the quiz-grader bot:
In ai/solver.py: remove the update_question call (and its import). solve_and_grade(question_id) should now only read the row, solve, grade, and return {"correct_answer", "explanation", "is_correct"} or None. Add a comment noting the function is side-effect-free by design: no DB writes, so it can be unit tested and reused anywhere.
In bot/handlers.py (photo handler): after solve_and_grade() returns a non-None dict, call update_question(question_id, correct_answer=..., explanation=..., is_correct=1 if result["is_correct"] else 0) and then send the Telegram ✅/❌ + explanation reply. If it returns None, send the existing fallback reply ("Couldn't solve this one — try a clearer photo.") and do NOT touch the DB row.
Wrap the update_question call in its own try/except: if the DB write fails, log it and still attempt to send the user the answer reply (solving worked; the user shouldn't lose the result because of a save hiccup).
Update the function docstring in solver.py to state it does not write to the DB.
Keep the code minimal and commented — the user is learning and needs to understand every part.
```

## What I learned

> Review the code the AI gives you — don't just run it. The first version worked, but the DB write living inside the solver blurred the line between _solving_ and _saving_. Splitting them means each failure mode is explicit, and the solver becomes a pure function I can unit test without touching the database.

This is the second time this week the fix wasn't "make the code work" but "make the code _honest_" — clear about what it does, where it writes, and what fails when.
