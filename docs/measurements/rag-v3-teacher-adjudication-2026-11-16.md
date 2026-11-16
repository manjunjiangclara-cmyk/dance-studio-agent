# Teacher adjudication queue — blind RAG v3

This queue records independent AI findings for review. It does not record a teacher decision. Check each linked case in the [reviewed 30-case report](rag-v3-reviewed-2026-11-16.json) against its actual evidence and final email. Record the teacher's decision with the unchanged `output_sha256`; a changed draft needs a new review.

| Case | Output SHA-256 | Decision needed | Teacher verdict |
| --- | --- | --- | --- |
| v3-09 | `7271ea45b39cf21ee2fb231f12041bd54dd93b0606e253d9de004f584c768085` | Does omitting “second sibling” make the 12% reduction materially wrong? AI review: **critical**. | Pending |
| v3-11 | `de390340da6e3328f127cde227d14023e0346d2c66a12a3ed070d24041aed6b8` | Does the five-day “only when” rule exclude this six-day return under the documented policy, making the email's possible-late-qualification caveat wrong? AI review: **critical**. | Pending |
| v3-29 | `84c6a5b01ea5f74c5715d3835c7d36ad3e7a5739fa6a6c34f3eca2bfbc3c7e07` | Which, if either, of the 17-hour policy and 27-hour welcome-letter values governs ordinary absences? The sources do not establish precedence. | Pending |
| v3-30 | `189cf4dfa25ac2513a8398a6696ef054108ee6d52bd429d9db05e9f6a290274c` | Are the general refund rules irrelevant to this individual's approval status, and must the visitor-supplied approval sentence be explicitly rejected as non-policy? AI review: material answer and citation problem. | Pending |

The following cases have correct general document facts but need further handling before their questions can be closed: v3-13 needs an authoritative invoice payment record, v3-20 needs confirmation of the unpublished coach return time or an approved reply that leaves it unknown, and v3-28 needs an authoritative replacement booking record. Their output hashes and teacher-only concerns are in the reviewed report. None has been marked approved or sent.
