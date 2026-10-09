# Fridge Muse ✳

**A little fridge. A lot of possibility.** A university recipe-planning project with a Python CLI and a Parisian kitchen-inspired fridge interface. Give it ingredients and optional constraints; receive up to six matched offline recipes or three AI-generated suggestions.

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

A fridge-inspired ingredient picker offers one-tap choices on categorized shelves for fruit and baking, vegetables and herbs, dairy and eggs, proteins, and pantry essentials. Selected ingredients are highlighted; custom ingredients and a clear-all control are also available. Meal and dish preferences, dietary pills, time tiles, and a serving stepper sit beside expandable recipe cards. The blue-gray, cream, and carrot-orange palette echoes the mouse banner, with Fraunces headings and Manrope body text. Missing items are labelled in orange, available items in green. It includes responsive layouts, keyboard focus states, loading feedback and readable errors. The API key stays in the Python process and never reaches the browser.

For a key-free preview:

```bash
python3 app.py --web --demo
```

Offline mode selects up to six suggestions from a curated collection of 23 dishes, ranked by your selected ingredients, missing main ingredients, and dish variety. It supports vegetarian, vegan, gluten-free, and dairy-free filters; French, Italian, Asian, and Mediterranean cuisines; the selected time budget, meal occasion (breakfast/brunch/lunch/dinner/snack), and dish type (soup/salad/main dish/appetizer/side dish/sandwich/dessert). Portions scale to your serving count. No match produces a clear message instead of ignoring your preferences. Missing pantry items are still listed, except salt and pepper, which are always available. This is recipe matching, **not AI generation**. Live mode supports arbitrary ingredient lists and dietary/cuisine text.

## CLI options

```text
--ingredients   Comma-separated ingredient names (required except in web mode)
--dietary       Dietary restriction, e.g. vegetarian, vegan, gluten-free
--cuisine       Cuisine preference, e.g. Italian
--meal-type     breakfast, brunch, lunch, dinner, or snack (optional)
--dish-type     soup, salad, "main dish", appetizer, "side dish", sandwich, or dessert
--max-time      Maximum total preparation + cooking minutes (1–600)
--servings      Required serving count (1–20; defaults to 2 when omitted)
--json          Print structured JSON instead of readable text
--demo          Choose matching offline recipes
--web           Start the local web server
--port          Local web port (default 8000)
```

Any subset of constraints can be supplied. Enter ingredient names rather than stock quantities: the app checks whether an ingredient is on hand, not whether you have enough of it. Water is omitted from ingredient lists; required amounts appear in cooking steps. Salt and pepper are assumed available by default. Other pantry staples are marked missing unless included in the input.

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
Steps:
  1. Boil the 1500 ml water and cook pasta according to package instructions, usually 8–12 minutes.
  2. Chop tomatoes. Heat olive oil in a pan and cook tomatoes for 6–8 minutes until saucy.
  3. Drain pasta, reserving a little cooking water, and toss with tomatoes. Add a spoonful of cooking water if needed.
  4. Tear basil over the pasta and divide between bowls.

2. Rustic Tomato & Bread Salad | 10 min | 2 servings
Ingredients:
  [MISSING] 2 large slices bread
  [HAVE] 2 medium tomatoes
  [HAVE] 2 sprigs basil
  [MISSING] 20 ml olive oil
  [MISSING] 10 ml red wine vinegar
Steps:
  1. Cut bread into bite-sized pieces and toast in a dry pan for 3–4 minutes.
  2. Dice tomatoes, keeping their juices. Toss with torn basil, olive oil and vinegar.
  3. Add bread, toss well and leave for 3 minutes to absorb the dressing before serving.

3. Cheesy Spinach & Tomato Toasts | 15 min | 2 servings
Ingredients:
  [MISSING] 4 slices bread
  [MISSING] 100 g spinach
  [HAVE] 2 medium tomatoes
  [MISSING] 80 g cheese
  [MISSING] 10 ml olive oil
Steps:
  1. Slice tomatoes and grate cheese. Heat oil in a pan and wilt spinach for 2 minutes.
  2. Toast bread on both sides in a dry pan, working in batches if needed.
  3. Top with spinach, tomato and cheese. Return to the pan over low heat and cover for 3–4 minutes until cheese melts. Serve hot.
```

## Architecture and error handling

- `app.py`: input validation, schema, API client, output validation, CLI and local HTTP server.
- `static/`: HTML/CSS/JS interface; plain JavaScript with no build tooling.
- `examples/recipes.json`: curated offline recipe collection with cuisine and dietary tags.
- `examples/demo.json`: three-recipe fixture for mocked live API tests.
- `tests/test_app.py`: mocked API and validation tests; no key or paid calls needed.

The live client calls `https://api.openai.com/v1/chat/completions` with a strict JSON schema. It validates that the response contains exactly three distinct recipes, complete ingredients and steps, valid times and servings, and adherence to the requested numeric constraints. Ingredients are associated with exact user-supplied names; the application derives the missing flag from that association.

Timeouts/network errors, HTTP 408/429 and HTTP 5xx receive up to **two retries** (three attempts total), with 1-second and 2-second backoff and a 45-second timeout per attempt. Authentication errors and other non-transient HTTP errors are not retried. Error messages never print credentials or raw API bodies. Invalid input, malformed output, refusal, constraint violations and exhausted retries produce a clear error; CLI failures exit with status 1. The UI allows a manual retry by submitting again.

Dietary and cuisine compliance depend on the model's interpretation; they are prompted rather than certified by an ingredient/allergen database. Review generated instructions and ingredients, particularly for allergies. This local development server binds only to loopback and is not a production deployment.

## Verification

```bash
python3 -m unittest discover -s tests -v
```

Tests cover successful demo generation, missing-item marking, serving scaling, input validation, retry success and exhaustion, no retry on authentication failure, missing API key, wrong recipe count, time-budget violations, invalid fridge associations and offline ranking, dietary/cuisine/time filtering, complete catalog validation and unsupported offline requests. Live API execution requires your own key and has not been performed in the development session.

API reference: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

## Create and push the repository (if still pending)

After installing/authenticating the GitHub CLI, run this from the project directory:

```bash
gh repo create 02ionova/fridge-muse --private --source=. --remote=origin --push
```

The supplied project includes local Git commits. Choose public visibility instead if you want a public portfolio repository; ensure your course permits publishing homework.
