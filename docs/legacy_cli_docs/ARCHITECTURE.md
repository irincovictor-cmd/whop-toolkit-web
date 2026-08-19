# WHOP TOOLKIT
## Architecture Blueprint
Version: 1.0

---

# Project Goal

The Whop Toolkit automates repetitive tasks involved in creating Whop clips while keeping AI (ChatGPT) responsible for creative decision-making.

The toolkit should NEVER replace human judgment.

Instead, it should:

• Download
• Organize
• Transcribe
• Analyze
• Score
• Export

while ChatGPT handles:

• Clip selection
• Viral analysis
• Editing advice
• CTA generation
• Compliance checking

---

# Philosophy

Rule #1

One module = One responsibility.

Never allow one module to perform multiple unrelated jobs.

---

Rule #2

Every analyzed video becomes a Project.

Nothing is stored globally except cache and logs.

---

Rule #3

Never rewrite working modules.

Always extend.

---

Rule #4

Every feature must be modular.

---

# Folder Structure

Whop Toolkit/

    whop.py
    config.py
    requirements.txt
    ARCHITECTURE.md

    core/

    modules/

    projects/

    cache/

    logs/

    templates/

---

# Core Objects

VideoProject

Contains

- title
- url
- video_id
- duration
- transcript
- candidates
- report
- campaign

---

Transcript

Contains

- language
- source
- segments
- full_text

---

CandidateClip

Contains

- start
- end
- duration
- text
- scores

---

Report

Contains

- rankings
- editing notes
- captions
- CTA
- compliance

---

# Modules

Downloader

Responsible ONLY for downloading.

Never analyzes.

---

Transcript Engine

Responsible ONLY for obtaining transcripts.

Order

1. YouTube transcript

2. Whisper fallback

---

Analyzer

Responsible ONLY for finding candidate clips.

---

Scorer

Responsible ONLY for assigning scores.

Never downloads.

Never edits.

---

Exporter

Responsible ONLY for creating reports.

---

Utils

Reusable helper functions.

No business logic.

---

# Project Workflow

Paste URL

↓

Create VideoProject

↓

Download Transcript

↓

Generate Candidate Clips

↓

Score Candidates

↓

Export Report

↓

User Chooses Clip

↓

Download Clip

↓

Edit

↓

Upload

---

# AI Responsibilities

ChatGPT performs

- Viral analysis

- Clip recommendations

- Editing advice

- Hooks

- CTA

- Compliance

Toolkit performs

- Downloads

- Transcripts

- Organization

- Reports

---

# Future Features

Version 1

✅ Transcript

✅ Download Clip

✅ Reports

---

Version 2

Candidate detection

Automatic scoring

---

Version 3

Campaign templates

Whop compliance checker

---

Version 4

Automatic captions

Title generator

Hashtag generator

---

Version 5

Multiple campaigns

Analytics

Historical database

Performance tracking

---

# Coding Standards

Every function should perform ONE task.

Avoid duplicate code.

Always use utility functions.

Every module must be testable independently.

---

# Project Motto

Automate the repetitive.

Leave the creative to humans.