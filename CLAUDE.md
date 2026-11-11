# nvwabase-gk — core design principle

## This is a general platform, not an abstract base

nvwabase-gk ships as a complete, working, general multi-agent system. It runs on
general problems out of the box. It is NOT an abstract framework that must be
filled in with a domain before it does anything.

Rules that follow from this, for anyone (human or agent) working on this repo:

1. **The base has no domain.** The commander orders, the toolbox, the engine, the
   supervisor, and the default docs are domain-free and must stay that way. No
   security, incident-response, or any other domain vocabulary in the base
   mechanism, base docs, or base tests.

2. **A domain is an optional, additive specialization**: a specialized commander
   skill, mission templates, a fact-kind vocabulary, and KB entries. Loading one
   specializes the general system into a bespoke version. The base must work with
   zero specialization.

3. **Examples direct writing; they do not get baked in.** Using an example domain
   to make the docs and skills concrete is fine. Letting that domain's assumptions
   leak into the general mechanism is the failure this note exists to prevent. If
   you catch yourself writing a base file that only makes sense for one kind of
   work, stop and generalize it.

4. **Watch for leaked domain assumptions in general mechanism.** Example: a
   confirm-gated intent is the general "gate a risky or irreversible action"
   mechanism — do not name or shape it as one domain's version of that (it is not
   "containment", it is not "flag submission"). Typed facts are a free-form slug —
   do not hardcode one domain's vocabulary as if it were the vocabulary. The
   neutral default vocabulary is `source`, `finding`, `artifact`, `decision`,
   `risk`, plus `note` as the default.

5. **If unsure whether something belongs in the base:** ask "does this make sense
   for a user who has never heard of any example domain?" If no, it belongs in a
   specialization, not the base.
