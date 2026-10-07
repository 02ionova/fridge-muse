# Fridge Muse ✳

**A little fridge. A lot of possibility.** A university recipe-planning project with a Python CLI and a retro, sage-green fridge interface. Give it ingredients and optional constraints; receive three complete recipe suggestions.

## Setup

Requires **Python 3.10+**. No packages to install.

```bash
git clone https://github.com/02ionova/fridge-muse.git
cd fridge-muse
export OPENAI_API_KEY='your-own-key'
# Optional; choose a model that supports Chat Completions structured outputs:
export OPENAI_MODEL='gpt-4o-mini'
python3 app.py --ingredients 'eggs,tomatoes,cheese' --dietary vegetarian --max-time 30 --servings 2
```

The GitHub URL above is the intended repository location; repository creation may still be pending. If using the downloadable archive, extract it and run the same commands from its `fridge-muse` directory.

On Windows PowerShell, use `$env:OPENAI_API_KEY = 'your-own-key'`. Your OpenAI API account needs model access and API billing; a ChatGPT subscription does not provide an API key.

| Environment variable | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required for live recipe generation; server-side only | None |
| `OPENAI_MODEL` | Structured-output-compatible Chat Completions model | `gpt-4o-mini` |

`.env.example` documents the variables. **The app does not automatically load `.env` files**: export variables in your shell. `.env` and variants are ignored by Git. Never paste an actual key into source, README, or frontend code.

## Creative web interface

```bash
python3 app.py --web
# Open http://127.0.0.1:8000
```

A illustrated-by-CSS fridge holds ingredient chips you can add and remove. Optional mood settings sit beside expandable recipe cards. Missing items are labelled in orange, available items in green. It includes responsive layouts, keyboard focus states, loading feedback and readable errors. The API key stays in the Python process and never reaches the browser.

For a key-free preview:

```bash
python3 app.py --web --demo
```

Demo mode uses three fixed vegetarian Italian recipes, marks ingredients against your current list, and scales quantities by servings. It is explicitly labelled and is **not AI generation**. It rejects unsupported dietary/cuisine constraints and budgets below 20 minutes. Live mode supports arbitrary ingredient lists and dietary/cuisine text.

## CLI options

```text
--ingredients   Comma-separated ingredient names (required except in web mode)
--dietary       Dietary restriction, e.g. vegetarian, vegan, gluten-free
--cuisine       Cuisine preference, e.g. Italian
--max-time      Maximum total preparation + cooking minutes (1–600)
--servings      Required serving count (1–20; defaults to 2 when omitted)
--json          Print structured JSON instead of readable text
--demo          Use fixed offline sample recipes
--web           Start the local web server
--port          Local web port (default 8000)
```

Any subset of constraints can be supplied. Enter ingredient names rather than stock quantities: the app checks whether an ingredient is on hand, not whether you have enough of it. Pantry staples are marked missing unless included in the input.

## Sample invocation and actual output

This reproducible example was executed in **offline demo mode**, without an API key. Live suggestions vary.

```bash
python3 app.py --demo --ingredients 'tomatoes,pasta,basil' --dietary vegetarian --cuisine Italian --max-time 20 --servings 2
```

```text
FRIDGE MUSE · DEMO

1. Tomato & Basil Pasta | 20 min | 2 servings
Ingredients:
  [HAVE] 200 g pasta
  [HAVE] 2 medium tomatoes
  [HAVE] 2 sprigs basil
  [MISSING] 20 ml olive oil
  [MISSING] enough to cover pasta water
Steps:
  1. Bring a pot of water to a boil. Add pasta and cook according to the package, usually 8–12 minutes.
  2. Meanwhile, chop tomatoes and heat olive oil in a pan. Cook tomatoes for 6–8 minutes, stirring.
  3. Drain pasta, reserving a little cooking water. Toss with tomatoes, adding cooking water to loosen the sauce.
  4. Tear basil over the pasta and divide evenly between servings.

2. Warm Tomato Bruschetta | 15 min | 2 servings
Ingredients:
  [MISSING] 2 large slices bread
  [HAVE] 2 medium tomatoes
  [HAVE] 2 sprigs basil
  [MISSING] 20 ml olive oil
Steps:
  1. Dice tomatoes and tear basil. Mix with half the olive oil.
  2. Brush bread with the remaining oil and toast in a pan over medium heat for 2–3 minutes per side.
  3. Top warm bread with the tomato mixture and divide evenly between servings.

3. Rustic Tomato & Bread Salad | 10 min | 2 servings
Ingredients:
  [MISSING] 2 large slices bread
  [HAVE] 2 medium tomatoes
  [HAVE] 2 sprigs basil
  [MISSING] 20 ml olive oil
  [MISSING] to taste red wine vinegar
Steps:
  1. Cut bread into bite-sized pieces. Toast in a dry pan over medium heat for 3–4 minutes.
  2. Chop tomatoes, keeping their juices. Combine with bread, torn basil, olive oil and a little vinegar.
  3. Let stand for 3 minutes so the bread absorbs the dressing, then divide evenly between servings.
```

## Architecture and error handling

- `app.py`: input validation, schema, API client, output validation, CLI and local HTTP server.
- `static/`: HTML/CSS/JS interface; plain JavaScript with no build tooling.
- `examples/demo.json`: reproducible offline fixture.
- `tests/test_app.py`: mocked API and validation tests; no key or paid calls needed.

The live client calls `https://api.openai.com/v1/chat/completions` with a strict JSON schema. It validates that the response contains exactly three distinct recipes, complete ingredients and steps, valid times and servings, and adherence to the requested numeric constraints. Ingredients are associated with exact user-supplied names; the application derives the missing flag from that association.

Timeouts/network errors, HTTP 408/429 and HTTP 5xx receive up to **two retries** (three attempts total), with 1-second and 2-second backoff and a 45-second timeout per attempt. Authentication errors and other non-transient HTTP errors are not retried. Error messages never print credentials or raw API bodies. Invalid input, malformed output, refusal, constraint violations and exhausted retries produce a clear error; CLI failures exit with status 1. The UI allows a manual retry by submitting again.

Dietary and cuisine compliance depend on the model's interpretation; they are prompted rather than certified by an ingredient/allergen database. Review generated instructions and ingredients, particularly for allergies. This local development server binds only to loopback and is not a production deployment.

## Verification

```bash
python3 -m unittest discover -s tests -v
```

Tests cover successful demo generation, missing-item marking, serving scaling, input validation, retry success and exhaustion, no retry on authentication failure, missing API key, wrong recipe count, time-budget violations, invalid fridge associations and unsupported demo constraints. Live API execution requires your own key and has not been performed in the development session.

API reference: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

## Create and push the repository (if still pending)

After installing/authenticating the GitHub CLI, run this from the project directory:

```bash
gh repo create 02ionova/fridge-muse --private --source=. --remote=origin --push
```

The supplied project includes local Git commits. Choose public visibility instead if you want a public portfolio repository; ensure your course permits publishing homework.
