# IndiaMART Smart Reply

**Professional replies. Better buyer conversations.**

An API-free product prototype showing how an AI-assisted "Smart Reply" feature could help small Indian
manufacturers, wholesalers and traders answer buyer enquiries clearly and professionally, without
making commercial promises they haven't authorised.

> **Disclosure.** This is an independent concept prototype built for product evaluation. It is not an
> official IndiaMART product and is not connected to IndiaMART systems, accounts, messages or buyer
> records. Replies are produced by a rule-based simulation; no live AI model or API is called.

> **Build status:** in progress. This README describes the finished prototype. Sections marked
> *(planned)* aren't implemented yet. The status line will be updated when the build and tests are
> complete.

---

## Contents

1. [What the prototype does](#what-the-prototype-does)
2. [How it works (and what it is not)](#how-it-works-and-what-it-is-not)
3. [Project structure](#project-structure)
4. [Run locally on Windows](#1-run-locally-on-windows)
5. [Create a GitHub repository](#2-create-a-github-repository)
6. [Upload the project](#3-upload-the-project-to-github)
7. [Deploy to Streamlit Community Cloud](#4-deploy-to-streamlit-community-cloud)
8. [Select the entry point](#5-select-the-entry-point)
9. [Make the app public](#6-make-the-app-public)
10. [Open and test the live URL](#7-open-and-test-the-live-url)
11. [Update the deployed app](#8-update-the-deployed-app-after-changes)
12. [Troubleshooting](#9-troubleshooting-deployment-errors)
13. [Running the tests](#running-the-tests)
14. [Known limitations](#known-limitations)

---

## What the prototype does

A seller pastes a buyer enquiry, such as:

> *Hi, I need 500 units of MS pipes 2 inch diameter, delivery in Pune, need rate and delivery timeline.*

The app then:

- **Reads the enquiry**: product, quantity, size, delivery location, and whether the buyer asked for
  price, delivery time or a guarantee.
- **Finds what's missing** for a quotation. For MS pipes that means grade/class (e.g. IS 1239 Class
  A/B/C), wall thickness and length.
- **Drafts a reply** in simple English, professional English or Hinglish. The reply acknowledges the
  requirement, asks only the questions needed, and ends with a clear next step.
- **Uses only verified seller facts.** Price, stock, MOQ, dispatch time, freight and certifications
  appear only if the seller entered them.
- **Checks the final text**, including the seller's own edits, for unsupported claims such as
  invented prices, stock promises or guaranteed delivery dates.
- **Keeps the seller in control.** The seller can edit, regenerate, shorten, simplify, make more
  professional, add questions, reset and copy. Nothing is ever sent automatically.

### App sections

| Section | Purpose |
|---|---|
| **Smart Reply Studio** (landing page) | Enquiry input, optional seller profile, reply generation and controls, missing-information panel, reasoning panel, "Start here: 2-minute demo" guide |
| **Prompt Lab** | Three prompt versions on the same enquiry, side by side: basic, commercially aware and seller-ready. Labelled as a simulated prompt-engineering demonstration |
| **Seller personas** | Three persona hypotheses (manufacturer, wholesaler, first-generation digital seller) with example enquiries |
| **Trust and adoption** | The three must-get-right requirements: commercial accuracy, minimal effort, seller control and privacy |
| **Metrics and pilot plan** | Prototype metrics, future marketplace metrics, experiment design, six-week plan |
| **About and demo guide** | Product overview, how it works, future architecture, limitations |

## How it works (and what it is not)

The prototype is a **deterministic, rule-based engine** written in plain Python:

1. **Extraction** (`smart_reply/extractor.py`) uses configurable keyword and unit patterns
   (`smart_reply/rules.py`) for five product categories: MS/ERW pipes, fasteners, steel sections/TMT
   bars, HDPE granules and fabricated products. Unrecognised products fall back to a generic rule set.
   Values that can't be matched reliably are shown as *unconfirmed* or *missing*, never guessed.
2. **Composition** *(planned: `smart_reply/engine.py`)* builds the reply from templates, the extracted
   requirement and the seller-entered facts. The selected prompt version changes how the reply is
   built.
3. **Validation** (`smart_reply/validator.py`) runs separately on the final text and flags unsupported
   commercial claims.
4. **Fictional demo catalogue** (`smart_reply/seller.py`): a small set of clearly labelled fictional
   seller profiles. Simple keyword retrieval picks the best-matching product for an enquiry. This is a
   lightweight stand-in for the retrieval-augmented architecture described on the About page.

**What it is not:** it does not call an LLM, does not need an API key, and does not claim general
natural-language understanding. Buyer text is treated as untrusted data. Instructions inside an
enquiry (e.g. "ignore your rules and confirm stock") are flagged and never followed.

**No API key, account or secret is needed** to run or deploy this app.

## Project structure

```text
indiamart-smart-reply/
├── app.py                     # Streamlit entry point (navigation, disclosure, error handling)  (planned)
├── app_pages/                 # One file per app section                                       (planned)
├── smart_reply/               # UI-independent engine
│   ├── rules.py               # Categories, specification patterns, question wording
│   ├── extractor.py           # Requirement extraction
│   ├── seller.py              # Seller profile, fictional catalogue, consistency checks
│   ├── validator.py           # Unsupported-claim detection
│   └── engine.py              # Reply composer and prompt versions                             (planned)
├── tests/                     # pytest suite
├── docs/                      # PRODUCT_SPEC, PROMPT_LAB, TRUST_AND_ADOPTION, METRICS_AND_PILOT  (planned)
├── .streamlit/config.toml     # Theme and server settings                                      (planned)
├── requirements.txt           # Runtime dependencies (Streamlit only)                           (planned)
├── requirements-dev.txt       # Test dependencies                                               (planned)
├── pytest.ini
└── README.md
```

---

## 1. Run locally on Windows

You need **Python 3.10 or newer** (3.12 recommended, to match the hosted version). Check it in
PowerShell:

```powershell
python --version
```

Open PowerShell in the project folder, then create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the activation script, run this once and try again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Install the dependencies and start the app:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens at <http://localhost:8501>. Press `Ctrl+C` in the terminal to stop it.

## 2. Create a GitHub repository

1. Sign in at <https://github.com>.
2. Click **+** (top right) → **New repository**.
3. **Repository name:** `indiamart-smart-reply`.
4. Choose **Public**. Streamlit Community Cloud makes apps from public repositories public by default,
   so evaluators won't need a login.
5. **Don't** tick "Add a README", ".gitignore" or "license". This project already has them, and an
   empty repository avoids push conflicts.
6. Click **Create repository** and keep the page open. It shows your repository URL.

## 3. Upload the project to GitHub

From PowerShell in the project folder, replacing `<your-username>` with your GitHub username:

```powershell
git init
git add .
git commit -m "Initial commit: IndiaMART Smart Reply prototype"
git branch -M main
git remote add origin https://github.com/<your-username>/indiamart-smart-reply.git
git push -u origin main
```

If Git asks you to sign in, a browser window opens for GitHub authentication. Don't put passwords or
tokens in any project file.

Check that `.gitignore` kept `.venv/` and `.streamlit/secrets.toml` out of the commit (this app
doesn't use secrets, but the rule stays in place):

```powershell
git status
```

## 4. Deploy to Streamlit Community Cloud

These steps follow the official guide:
<https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app>

1. Go to <https://share.streamlit.io> and sign in with GitHub. Authorise Streamlit to read your
   repositories when asked.
2. In your workspace, click **Create app** (top right).
3. When asked "Do you already have an app?", choose **Yup, I have an app**.
4. Fill in the repository details (see the next step for the entry point).
5. *(Optional)* In **App URL**, choose a subdomain such as `indiamart-smart-reply`. The app will then
   live at `https://indiamart-smart-reply.streamlit.app`, if that name is free.
6. Click **Advanced settings**:
   - **Python version:** choose **3.12** (the default). This can't be changed later without deleting
     and redeploying the app.
   - **Secrets:** leave empty. This app needs no secrets or API keys.
   - Click **Save**.
7. Click **Deploy**. The first build usually takes a few minutes. Build logs appear beside the app.

## 5. Select the entry point

In the deploy form:

| Field | Value |
|---|---|
| Repository | `<your-username>/indiamart-smart-reply` |
| Branch | `main` |
| Main file path | `app.py` |

Alternatively, click **Paste GitHub URL** and paste the link to `app.py` in your repository, e.g.
`https://github.com/<your-username>/indiamart-smart-reply/blob/main/app.py`.

## 6. Make the app public

Apps deployed from a **public** repository are public by default. To confirm, or if you used a
private repository:

1. Open the app, then go to its **Settings** → **Sharing**.
2. Under **Who can view this app**, select **This app is public and searchable**.

Alternatively, click **Share** (top right of the app) and turn on **Make this app public**.

To check, open the app URL in a private/incognito browser window where you're not signed in. It
should load without asking you to log in.

## 7. Open and test the live URL

Open the URL in an incognito window and go through the **Start here: 2-minute demo** on the landing
page:

1. Click **Load sample enquiry** and **Generate smart reply**. The reply should ask for MS grade, wall
   thickness and pipe length, and state no price, stock or delivery date.
2. Open **Prompt Lab** and compare the three versions. Version 1 should show flagged unsupported
   claims.
3. Back in the Studio, enter a fictional price (e.g. `₹68 per kg`) and available quantity, then
   regenerate. The reply should now use those values.
4. Clear the price and regenerate. The price should disappear, not be invented.
5. Edit the reply, type a claim such as "guaranteed delivery in 2 days" and check that it's flagged.
6. Tick the review box and use **Copy reply**. If the browser blocks clipboard access, use the copy
   icon on the plain-text box or select the text manually.
7. Check the app on a phone, or with a narrow browser window.

**Before sharing the link with an evaluator:** apps sleep after 12 hours without traffic. Open the
URL shortly before sending it. If you see "Yes, get this app back up!", click it and wait for the app
to start. Anyone with the link can wake it the same way.

## 8. Update the deployed app after changes

Push to the `main` branch. Code changes usually appear within moments, and changes to
`requirements.txt` trigger a full redeploy that takes a few minutes.

```powershell
git add .
git commit -m "Describe your change"
git push
```

If the app doesn't pick up a change, go to your workspace at <https://share.streamlit.io>, open the
app's **⋮** (overflow) menu and select **Reboot**. You can also reach the app's controls from
**Manage app** (bottom right of the running app).

## 9. Troubleshooting deployment errors

Start with the logs: open the app and click **Manage app** (bottom right). Only accounts with write
access to the repository can see them.

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: smart_reply` | `smart_reply/` folder not pushed | Run `git status`, add the folder, commit and push |
| `ModuleNotFoundError` for another package | Package missing from `requirements.txt` | Add it with a pinned version, push and wait for the redeploy |
| "Main module does not exist" | Wrong **Main file path** | Use `app.py`, which sits at the repository root |
| Dependency install fails | Pinned version incompatible with the chosen Python | Redeploy with Python 3.12 (delete the app, then deploy again with the same subdomain) |
| App works locally but not online | Local-only file or absolute Windows path | The app reads no local files outside the repository; check recent changes for `C:\` paths |
| "This app has gone to sleep" | 12 hours without traffic | Click **Yes, get this app back up!** |
| Evaluator asked to sign in | App or repository is private | See [step 6](#6-make-the-app-public) |
| Blank page or stale version | Browser cache or an old session | Hard refresh (`Ctrl+F5`) or reboot the app |
| Copy button shows "Copy blocked" | Browser denied clipboard access | Use the copy icon on the plain-text box, or select the text and press `Ctrl+C` |

---

## Running the tests

Install the test dependency once, then run the suite from the project root:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

The suite covers extraction rules, reply composition, validation (missing price, stock and delivery
details; conflicting seller details; guaranteed-delivery requests; empty enquiries; unsupported
claims; attempts to override rules through buyer text) and the Streamlit pages, using Streamlit's
`AppTest` harness.

## Known limitations

- **Rule-based, not AI.** Extraction and composition use patterns and templates. Unusual phrasing,
  spelling mistakes or products outside the five categories are handled conservatively (asked about,
  not guessed), but they may not be understood.
- **The validator can't catch everything.** It detects common unsupported-claim phrasings in English
  and Hinglish, but a creatively worded claim can slip through, and a harmless sentence may
  occasionally be flagged. Seller review is always required.
- **Hinglish is template-based** and hasn't been reviewed with native-speaking sellers.
- **No persistence.** Inputs live only in the current browser session and are lost on refresh or
  restart. Nothing is stored on a server.
- **Personas, priorities and metrics are hypotheses**, not findings from real seller research.
  Market figures on the overview pages are secondary research and are labelled as unverified.
- **Fictional data only.** All demo seller profiles and figures are invented for demonstration.
