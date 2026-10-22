# Automation case studies

Two write-ups of work already shipped, for the n8n community forum Jobs board,
the Make.com expert directory, Contra, and client conversations.

**Fill in the bracketed blanks before posting.** They're blank because I don't
know the numbers, and inventing them would fall apart the first time a client
asked a follow-up question. Even rough figures ("about 40 requests a week")
make these land harder than any adjective.

---

## 1. Membership intake with email verification

**Platform:** Make.com

**The problem.** Join requests to my Facebook groups arrived faster than anyone
could vet by hand, and the contact list that came out the other side was full of
junk and unverifiable addresses. Marketing was sending to emails that bounced,
which hurts deliverability on every later send.

**What I built.** A Make.com scenario that runs intake end to end:

1. A join request comes in and enters processing.
2. The email address is passed to a verification step.
3. The result branches — addresses that verify go into a clean list for later
   marketing; the rest are held back rather than silently added.

No manual sorting, and the list stays clean by construction instead of needing
a purge later.

**Result.** [Roughly how many requests per week? What share get filtered out?
If you know the bounce rate before vs after, that's the strongest number here.]

**Why it matters to a client.** This is the same shape as any lead-intake
pipeline: capture, validate, branch, route to a clean destination. Swap Facebook
for a web form and the marketing list for a CRM and it's a lead-qualification
build.

---

## 2. OpenAI inside a spreadsheet

**Platform:** OpenAI API + spreadsheet

**The problem.** The work already lived in a spreadsheet, but writing copy or
asking questions about that data meant copy-pasting out to a chat window and
back. Slow, and the context got lost every round trip.

**What I built.** Wired the OpenAI API directly into the sheet, so:

- A request typed into the sheet returns a generated response in place — the
  same back-and-forth you'd have in a chat window, without leaving the sheet.
- It reads the sheet's own rows and returns a *processed* answer, not just free
  text — so you can ask about the data rather than only generating around it.

**Result.** [What did this replace, and roughly how much time did it save per
week? How many rows/requests does it handle?]

**Why it matters to a client.** Most businesses keep their operational data in
sheets. This is the pattern for putting AI where the data already is instead of
asking people to change tools.

---

## Posting notes

**On the n8n/Make mismatch — not a problem.** The forum's jobs board carries
posts like *"AI Automation Engineer (n8n / Make / APIs)"*, so Make.com work
counts there. Say plainly that your shipped builds are Make.com and you also
work in n8n; don't imply the two above were built in n8n. If you want to close
the gap properly, rebuild the intake flow in n8n — it's a few hours, it's good
practice, and it gives you an n8n-native portfolio piece.

**Lead with the problem, not the tool.** Clients hire someone who understood
why the junk list mattered, not someone who lists connectors.

**Keep a fixed price in mind.** Productized offers convert better than hourly
bids. These two map to two sellable packages:
- *Lead intake + verification pipeline* — fixed price.
- *AI inside your spreadsheet* — fixed price.
