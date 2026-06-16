"""Curriculum editing API — skills enable/disable, tier names, coach feedback.

Permission model:

* **Club admin** of a club workspace, or the **owner** of a personal
  workspace, can edit (enable/disable skills, rename tiers, send + read
  feedback inbox).
* Editing (PATCH) endpoints are also plan-gated — only ``club_pro``,
  ``solo_coach`` and ``free_trial`` workspaces can mutate; ``club_starter``
  gets a 402 with an upgrade hint.
* Other roles (``head_coach``, ``coach``) can read the curriculum and send
  feedback notes to the admin, but cannot edit.
* Trainees/parents see nothing under ``/curriculum/*``.

See ``permissions.py`` for the central authz helpers.
"""
