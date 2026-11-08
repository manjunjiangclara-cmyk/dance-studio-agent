# Known-regression v1/v2 answer comparison

All questions were inspected before this diagnostic. Initial and refined v2 have different prompt/payload hashes. Refined v2 was run on only 16 artifacts. No semantic acceptance claim or fresh-holdout claim is made. Independent review is pending because the agent hit its usage limit.

## gen-held_out-01 / actual

How far ahead must our host request a workshop led by a visiting artist?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The host must submit the visiting artist booking request at least 18 calendar days before the first workshop. \[E4bb99ad4f7a8a60781e23afb\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E4bb99ad4f7a8a60781e23afb: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:a38374140013f8ae41ed670ed346a084c667fff6f3fff1fefc7ce9539906d0d6 \[696, 808\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The guest office requires a visiting artist booking request at least 18 calendar days before the first workshop.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Your host must submit the visiting artist booking request at least 18 calendar days before the first workshop; count the first teaching day as day zero. \[E4bb99ad4f7a8a60781e23afb\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E4bb99ad4f7a8a60781e23afb: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:a38374140013f8ae41ed670ed346a084c667fff6f3fff1fefc7ce9539906d0d6 \[696, 808\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The guest office requires a visiting artist booking request at least 18 calendar days before the first workshop.
- E4bb99ad4f7a8a60781e23afb: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:a38374140013f8ae41ed670ed346a084c667fff6f3fff1fefc7ce9539906d0d6 \[918, 959\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Count the first teaching day as day zero.


## gen-held_out-01 / standard

How far ahead must our host request a workshop led by a visiting artist?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The host must submit the visiting artist booking request at least 18 calendar days before the first workshop; the first teaching day counts as day zero. \[E4bb99ad4f7a8a60781e23afb\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E4bb99ad4f7a8a60781e23afb: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:a38374140013f8ae41ed670ed346a084c667fff6f3fff1fefc7ce9539906d0d6 \[696, 959\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The guest office requires a visiting artist booking request at least 18 calendar days before the first workshop. A request records the teaching theme, room, age band, planned equipment and whether an observer will attend. Count the first teaching day as day zero.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The host must submit the visiting artist booking request at least 18 calendar days before the first workshop; the first teaching day counts as day zero. \[E4bb99ad4f7a8a60781e23afb\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E4bb99ad4f7a8a60781e23afb: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:a38374140013f8ae41ed670ed346a084c667fff6f3fff1fefc7ce9539906d0d6 \[696, 808\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The guest office requires a visiting artist booking request at least 18 calendar days before the first workshop.
- E4bb99ad4f7a8a60781e23afb: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:a38374140013f8ae41ed670ed346a084c667fff6f3fff1fefc7ce9539906d0d6 \[918, 959\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Count the first teaching day as day zero.


## gen-held_out-02 / actual

Can our host move a confirmed guest class without a fee, and how much notice is needed?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. \[E396e5d9d75dda1219a34967a\]

The move must retain the same visiting teacher and cohort. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1344\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1345, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The change must retain the same visiting teacher and cohort.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A host may move a confirmed guest workshop once without an administration fee, provided they give seven full days of notice and retain the same visiting teacher and cohort. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. The change must retain the same visiting teacher and cohort.


## gen-held_out-02 / standard

Can our host move a confirmed guest class without a fee, and how much notice is needed?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice; the change must retain the same visiting teacher and cohort. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. The change must retain the same visiting teacher and cohort.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A host may move a confirmed guest workshop once without an administration fee if they give seven full days of notice, and the move must retain the same visiting teacher and cohort. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1344\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1345, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The change must retain the same visiting teacher and cohort.


## gen-held_out-03 / actual

The visiting choreographer cancelled. What choices does the office give participants and when is a refund due?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The office offers participants either a replacement workshop or a full workshop-fee refund, and records each participant’s choice. \[E396e5d9d75dda1219a34967a\]

The full workshop-fee refund is offered within ten business days. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1915\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund within ten business days. The office records each participant's choice.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1869\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund within ten business days.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

When a visiting artist cancels, the office offers participants a replacement workshop or a full workshop-fee refund. \[E396e5d9d75dda1219a34967a\]

The refund is offered within ten business days. \[E396e5d9d75dda1219a34967a\]

A regular class credit is not substituted unless the participant expressly chooses it. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1843\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1817, 1868\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: a full workshop-fee refund within ten business days
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1916, 1999\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A regular class credit is not substituted without the participant's express choice.


## gen-held_out-03 / standard

The visiting choreographer cancelled. What choices does the office give participants and when is a refund due?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

When a visiting artist cancels, the office offers participants either a replacement workshop or a full workshop-fee refund within ten business days. \[E396e5d9d75dda1219a34967a\]

The office records each participant’s choice; it does not substitute a regular class credit without the participant’s express choice. \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1869\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund within ten business days.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1870, 1999\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office records each participant's choice. A regular class credit is not substituted without the participant's express choice.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \[\]



## gen-held_out-04 / actual

How early should a visiting teacher arrive for their first teaching session?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A visiting teacher must check in 25 minutes before their first scheduled teaching session. \[E2df483ea821a9fcce3164537\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E2df483ea821a9fcce3164537: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:3b0bff0e340eb61f7c22774e33ea3b38352f4087893e859c41eebdd493e1f199 \[585, 673\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Visiting artists must check in 25 minutes before their first scheduled teaching session.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A visiting teacher should check in 25 minutes before their first scheduled teaching session. \[E2df483ea821a9fcce3164537\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E2df483ea821a9fcce3164537: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:3b0bff0e340eb61f7c22774e33ea3b38352f4087893e859c41eebdd493e1f199 \[585, 673\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Visiting artists must check in 25 minutes before their first scheduled teaching session.


## gen-held_out-04 / standard

How early should a visiting teacher arrive for their first teaching session?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A visiting teacher must check in 25 minutes before their first scheduled teaching session. \[E2df483ea821a9fcce3164537\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E2df483ea821a9fcce3164537: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:3b0bff0e340eb61f7c22774e33ea3b38352f4087893e859c41eebdd493e1f199 \[585, 673\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Visiting artists must check in 25 minutes before their first scheduled teaching session.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A visiting teacher must check in 25 minutes before their first scheduled teaching session. \[E2df483ea821a9fcce3164537\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E2df483ea821a9fcce3164537: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:3b0bff0e340eb61f7c22774e33ea3b38352f4087893e859c41eebdd493e1f199 \[585, 673\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Visiting artists must check in 25 minutes before their first scheduled teaching session.


## gen-held_out-05 / actual

Can an artist message a child directly to arrange private follow-up lessons?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

No. A visiting artist must not arrange private follow-up coaching with a minor through the minor’s personal messaging account; requests should go to the office, and the guardian receives the proposal. \[E58da99f19ddb0b0935bc52f1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2015, 2203\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: A visiting artist must not arrange private follow-up coaching with a minor through the minor's personal messaging account. Requests go to the office and the guardian receives the proposal.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. A visiting artist must not arrange private follow-up coaching with a minor through the minor’s personal messaging account. Requests should go to the office, and the guardian should receive the proposal. \[E58da99f19ddb0b0935bc52f1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2015, 2137\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: A visiting artist must not arrange private follow-up coaching with a minor through the minor's personal messaging account.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2138, 2203\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Requests go to the office and the guardian receives the proposal.


## gen-held_out-05 / standard

Can an artist message a child directly to arrange private follow-up lessons?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

No. A visiting artist must not arrange private follow-up coaching with a minor through the minor's personal messaging account. \[E58da99f19ddb0b0935bc52f1\]

Requests for private follow-up coaching should go to the office, and the guardian receives the proposal. \[E58da99f19ddb0b0935bc52f1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2015, 2137\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: A visiting artist must not arrange private follow-up coaching with a minor through the minor's personal messaging account.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2138, 2203\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Requests go to the office and the guardian receives the proposal.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. A visiting artist must not arrange private follow-up coaching with a minor through the minor’s personal messaging account. \[E58da99f19ddb0b0935bc52f1\]

Requests for private follow-up coaching should go to the office, and the guardian receives the proposal. \[E58da99f19ddb0b0935bc52f1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2015, 2137\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: A visiting artist must not arrange private follow-up coaching with a minor through the minor's personal messaging account.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[2138, 2203\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Requests go to the office and the guardian receives the proposal.


## gen-held_out-06 / actual

Does using a different guest teacher require new confirmation if the workshop keeps its name?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Yes. If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same. \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Yes. If the named guest is replaced by another artist, a fresh booking confirmation is required even if the workshop title stays the same. \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


## gen-held_out-06 / standard

Does using a different guest teacher require new confirmation if the workshop keeps its name?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Yes. If the named guest is replaced by a different artist, a fresh booking confirmation is required even when the workshop title stays the same. \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Yes. Replacing the named guest with another artist requires a fresh booking confirmation even if the workshop title stays the same. \[Ec05c3d9ba0bcfc11d97dbf88\] \[E396e5d9d75dda1219a34967a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1406, 1519\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Replacing the guest, changing an adult class into a youth class, or adding a second day is a new booking request.


## gen-held_out-07 / actual

When can a guest teach without a studio host, and what rule applies if a 15-year-old joins?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A guest may teach without a host in the room for an adult-only workshop after the duty lead signs an exception for that dated session. \[E58da99f19ddb0b0935bc52f1\]

If a 15-year-old joins, the workshop must have a rostered studio host present throughout the teaching period, because the requirement applies to any participant under 16. \[E9770871dad848b9fd89e1d7f\] \[E58da99f19ddb0b0935bc52f1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1514, 1754\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: For an adult-only guest workshop, the artist may teach without a host in the room after the duty lead signs the adult-session exception. The exception is specific to the dated session and cannot be copied to a youth workshop later that day.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3295, 3424\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Every guest workshop containing any participant under 16 must have a rostered studio host present throughout the teaching period.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1826, 1896\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: A person who turns 16 next week is still under 16 on today's register.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A guest may teach without a host in the room for an adult-only guest workshop only after the duty lead signs the adult-session exception. That exception applies only to the dated session and cannot be carried over to a youth workshop later that day; it does not remove sign-in, emergency briefing, or room-closing duties. \[E58da99f19ddb0b0935bc52f1\]

If a 15-year-old joins, the workshop includes a participant under 16 and must have a rostered studio host present throughout the teaching period, including for one-to-one coaching. A remote host does not count as present. \[E9770871dad848b9fd89e1d7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1514, 1650\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: For an adult-only guest workshop, the artist may teach without a host in the room after the duty lead signs the adult-session exception.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1651, 1754\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The exception is specific to the dated session and cannot be copied to a youth workshop later that day.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1755, 1825\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: It does not remove sign-in, emergency briefing or room-closing duties.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3295, 3424\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Every guest workshop containing any participant under 16 must have a rostered studio host present throughout the teaching period.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3425, 3476\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: This condition also applies to one-to-one coaching.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3477, 3540\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A remote host available by telephone does not count as present.


## gen-held_out-07 / standard

When can a guest teach without a studio host, and what rule applies if a 15-year-old joins?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A guest may teach an adult-only workshop without a host in the room after the duty lead signs the adult-session exception; that exception applies only to the dated session and cannot be carried over to a youth workshop later that day. \[E58da99f19ddb0b0935bc52f1\]

If a 15-year-old joins, the workshop includes a participant under 16 and must have a rostered studio host present throughout the teaching period; this also applies to one-to-one coaching, and a remote host by telephone does not count as present. \[E9770871dad848b9fd89e1d7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1514, 1754\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: For an adult-only guest workshop, the artist may teach without a host in the room after the duty lead signs the adult-session exception. The exception is specific to the dated session and cannot be copied to a youth workshop later that day.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3295, 3540\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Every guest workshop containing any participant under 16 must have a rostered studio host present throughout the teaching period. This condition also applies to one-to-one coaching. A remote host available by telephone does not count as present.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A guest may teach without a host in the room only for an adult-only guest workshop after the duty lead signs an exception for that dated session; the exception does not transfer to a youth workshop later that day. The exception also does not remove sign-in, emergency briefing, or room-closing duties. \[E58da99f19ddb0b0935bc52f1\]

If a 15-year-old joins, the workshop must have a rostered studio host present throughout the teaching period; a host available remotely by telephone does not count as present. \[E9770871dad848b9fd89e1d7f\] \[Efbf440f3c1a406fecd32771c\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1514, 1650\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: For an adult-only guest workshop, the artist may teach without a host in the room after the duty lead signs the adult-session exception.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1651, 1754\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The exception is specific to the dated session and cannot be copied to a youth workshop later that day.
- E58da99f19ddb0b0935bc52f1: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:94474b133aa78e884694dd0d0987d5b21eb4168cbf75e49c18f76e94a3f8e382 \[1755, 1825\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: It does not remove sign-in, emergency briefing or room-closing duties.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3295, 3424\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Every guest workshop containing any participant under 16 must have a rostered studio host present throughout the teaching period.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3477, 3540\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A remote host available by telephone does not count as present.
- Efbf440f3c1a406fecd32771c: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:71ea9d8e7442b204c35ef63b2cb8fc93bea401dacf279d5604d125aed7489f3c \[4424, 4565\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: At lunch the artist reads the afternoon register and notices a 15-year-old participant, so the office arranges a host for that whole session.


## gen-held_out-08 / actual

We are replacing the guest rather than moving the same visit. Can we use the free move allowance or do we need a fresh booking?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The free move allowance does not apply when you replace the guest; a permitted move must retain the same visiting teacher and cohort. \[E396e5d9d75dda1219a34967a\]

Replacing the guest is a new booking request, and a fresh booking confirmation is required. \[E396e5d9d75dda1219a34967a\] \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. The change must retain the same visiting teacher and cohort.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1406, 1519\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Replacing the guest, changing an adult class into a youth class, or adding a second day is a new booking request.
- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The free move allowance does not apply when replacing the guest: a move without an administration fee is allowed only with seven full days of notice and when the same visiting teacher and cohort are retained. \[E396e5d9d75dda1219a34967a\]

Replacing the named guest requires a fresh booking confirmation, even if the workshop title stays the same. \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. The change must retain the same visiting teacher and cohort.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1406, 1519\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Replacing the guest, changing an adult class into a youth class, or adding a second day is a new booking request.
- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


## gen-held_out-08 / standard

We are replacing the guest rather than moving the same visit. Can we use the free move allowance or do we need a fresh booking?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The free move allowance does not apply when replacing the guest: it applies only if the change retains the same visiting teacher and cohort. \[E396e5d9d75dda1219a34967a\]

Replacing the guest requires a new booking request and a fresh booking confirmation. \[E396e5d9d75dda1219a34967a\] \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. The change must retain the same visiting teacher and cohort.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1406, 1519\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Replacing the guest, changing an adult class into a youth class, or adding a second day is a new booking request.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1406, 1519\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Replacing the guest, changing an adult class into a youth class, or adding a second day is a new booking request.
- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The free move allowance applies only once, with seven full days of notice, and only if the same visiting teacher and cohort are retained. Replacing the guest is a new booking request, and a fresh booking confirmation is required, so you cannot use the free move allowance for that replacement. \[E396e5d9d75dda1219a34967a\] \[Ec05c3d9ba0bcfc11d97dbf88\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1225, 1405\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A confirmed guest workshop may be moved once without an administration fee if the host gives seven full days of notice. The change must retain the same visiting teacher and cohort.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1406, 1519\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Replacing the guest, changing an adult class into a youth class, or adding a second day is a new booking request.
- Ec05c3d9ba0bcfc11d97dbf88: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:1901e5a552b3c5820a9bc9960aa49168680c05c917ffbd790421c68041fa0d7c \[3303, 3438\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: If the named guest is replaced by another artist, a fresh booking confirmation is required even when the workshop title stays the same.


## gen-held_out-09 / actual

A youth workshop is cancelled by the guest: what options do participants receive, and what host requirement would still apply to a replacement youth session?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

When a visiting artist cancels, participants are offered either a replacement workshop or a full workshop-fee refund within ten business days. \[E396e5d9d75dda1219a34967a\]

The office records each participant’s choice; a regular class credit is not substituted unless the participant expressly chooses it. \[E396e5d9d75dda1219a34967a\]

For a replacement youth session that includes any participant under 16, a rostered studio host must be present throughout the teaching period. \[E9770871dad848b9fd89e1d7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1869\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund within ten business days.
- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1870, 1999\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office records each participant's choice. A regular class credit is not substituted without the participant's express choice.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3295, 3424\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Every guest workshop containing any participant under 16 must have a rostered studio host present throughout the teaching period.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

For a replacement guest workshop that includes any participant under 16, a rostered studio host must be present throughout the teaching period. A remote host does not meet this requirement; if the host must leave, teaching pauses until another rostered host takes over. \[E9770871dad848b9fd89e1d7f\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \[\]

- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3295, 3424\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: Every guest workshop containing any participant under 16 must have a rostered studio host present throughout the teaching period.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3477, 3540\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: A remote host available by telephone does not count as present.
- E9770871dad848b9fd89e1d7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:e6afdc60e4e18b73454f3fc44dd9a5f90f770389b5687909cc46892e530b14e2 \[3541, 3674\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: If the host must leave the building, teaching pauses until another rostered host takes over; the guest cannot waive this requirement.


## gen-held_out-09 / standard

A youth workshop is cancelled by the guest: what options do participants receive, and what host requirement would still apply to a replacement youth session?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

When a visiting artist cancels, participants are offered either a replacement workshop or a full workshop-fee refund within ten business days. \[E396e5d9d75dda1219a34967a\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1869\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund within ten business days.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

When a visiting artist cancels, the office offers participants either a replacement workshop or a full workshop-fee refund within ten business days, records each participant’s choice, and does not substitute a regular class credit without that participant’s express choice. \[E396e5d9d75dda1219a34967a\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \[\]

- E396e5d9d75dda1219a34967a: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:ca452e222d7d0a1b8c8c025e5b01c680e3d239c8e75eef518960ceb940327a47 \[1734, 1999\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: When a visiting artist cancels, the office offers either a replacement workshop or a full workshop-fee refund within ten business days. The office records each participant's choice. A regular class credit is not substituted without the participant's express choice.


## gen-held_out-10 / actual

After a residency runs in both buildings, which envelope is used for the final host handover sheet?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH. \[E7b20e19832e3b2e9caa1dc7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7b20e19832e3b2e9caa1dc7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:2bcee4b66f7f2842ad5a488472f0de81ffb2907da6bd41db11e5c69d57d773c6 \[7871, 8004\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH. \[E7b20e19832e3b2e9caa1dc7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7b20e19832e3b2e9caa1dc7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:2bcee4b66f7f2842ad5a488472f0de81ffb2907da6bd41db11e5c69d57d773c6 \[7871, 8004\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH.


## gen-held_out-10 / standard

After a residency runs in both buildings, which envelope is used for the final host handover sheet?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH. \[E7b20e19832e3b2e9caa1dc7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7b20e19832e3b2e9caa1dc7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:2bcee4b66f7f2842ad5a488472f0de81ffb2907da6bd41db11e5c69d57d773c6 \[7871, 8004\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH. \[E7b20e19832e3b2e9caa1dc7f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7b20e19832e3b2e9caa1dc7f: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:2bcee4b66f7f2842ad5a488472f0de81ffb2907da6bd41db11e5c69d57d773c6 \[7871, 8004\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: For a guest residency spanning both buildings, the final host handover sheet must be sealed in the green envelope marked GUEST NORTH.


## gen-held_out-11 / actual

For how many calendar days can a student normally keep a borrowed percussion instrument?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A student can normally keep a borrowed percussion instrument for 21 calendar days from the signed collection date; the collection day is day zero. \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[566, 734\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date. The collection day is day zero and the due date is written on the receipt.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A student normally keeps a borrowed percussion instrument for 21 calendar days, counted from the signed collection date; the collection day is day zero. \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[566, 690\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date. The collection day is day zero


## gen-held_out-11 / standard

For how many calendar days can a student normally keep a borrowed percussion instrument?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A student can normally keep a borrowed percussion instrument for 21 calendar days from the signed collection date; the collection day counts as day zero. \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[566, 734\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date. The collection day is day zero and the due date is written on the receipt.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A standard percussion instrument loan lasts 21 calendar days from the signed collection date; the collection day is day zero. \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[566, 690\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date. The collection day is day zero


## gen-held_out-12 / actual

How many business days before pickup must a student reserve a loan drum?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A student must reserve a loan instrument at least three business days before collection \(pickup\). \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[969, 1067\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: An enrolled student must reserve a loan instrument at least three business days before collection.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

An enrolled student must reserve a loan instrument at least three business days before collection. \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[969, 1067\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: An enrolled student must reserve a loan instrument at least three business days before collection.


## gen-held_out-12 / standard

How many business days before pickup must a student reserve a loan drum?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A student must reserve a loan drum at least three business days before collection \(pickup\). \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[969, 1067\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: An enrolled student must reserve a loan instrument at least three business days before collection.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A student must reserve a loan drum at least three business days before collection. \[E1a58a0389cbb57c04423a5e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a58a0389cbb57c04423a5e5: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:d22f0a98eb9a4a2de051191aeae9354fb0484b15bc083f8972023771c46ac67f \[969, 1067\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: An enrolled student must reserve a loan instrument at least three business days before collection.


## gen-held_out-13 / actual

Does a student need to close the loan drum case outdoors on a dry day?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Yes. Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather. \[E690d6b1d06b80286b0c51466\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E690d6b1d06b80286b0c51466: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:71e607c222db9259c4fc67ca6b65739f9d1577b51bf0beebea9bb88c9e1abedd \[1903, 2012\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Yes. The borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather. \[E690d6b1d06b80286b0c51466\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E690d6b1d06b80286b0c51466: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:71e607c222db9259c4fc67ca6b65739f9d1577b51bf0beebea9bb88c9e1abedd \[1903, 2012\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

Yes. Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather. \[E690d6b1d06b80286b0c51466\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E690d6b1d06b80286b0c51466: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:71e607c222db9259c4fc67ca6b65739f9d1577b51bf0beebea9bb88c9e1abedd \[1903, 2012\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather.


## gen-held_out-13 / standard

Does a student need to close the loan drum case outdoors on a dry day?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Yes. A student must carry borrowed percussion in its closed case whenever it is outdoors, including in dry weather. \[E690d6b1d06b80286b0c51466\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E690d6b1d06b80286b0c51466: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:71e607c222db9259c4fc67ca6b65739f9d1577b51bf0beebea9bb88c9e1abedd \[1903, 2012\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Yes. A student must carry the borrowed percussion in its closed case whenever it is outdoors, including in dry weather. \[E690d6b1d06b80286b0c51466\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E690d6b1d06b80286b0c51466: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:71e607c222db9259c4fc67ca6b65739f9d1577b51bf0beebea9bb88c9e1abedd \[1903, 2012\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

Yes. Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather. \[E690d6b1d06b80286b0c51466\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E690d6b1d06b80286b0c51466: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:71e607c222db9259c4fc67ca6b65739f9d1577b51bf0beebea9bb88c9e1abedd \[1903, 2012\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Borrowed percussion must be carried inside its closed case whenever it is outdoors, including in dry weather.


## gen-held_out-14 / actual

How soon must a borrower report a split drumhead or a loose metal part?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it. \[Ecaf4da2e8b2f3d22446f8694\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecaf4da2e8b2f3d22446f8694: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:f7bc67956f2920147b5d40d29b801e18090524d35093e690ab310547ac5303df \[598, 695\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it. \[Ecaf4da2e8b2f3d22446f8694\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecaf4da2e8b2f3d22446f8694: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:f7bc67956f2920147b5d40d29b801e18090524d35093e690ab310547ac5303df \[598, 695\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it.


## gen-held_out-14 / standard

How soon must a borrower report a split drumhead or a loose metal part?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it. \[Ecaf4da2e8b2f3d22446f8694\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecaf4da2e8b2f3d22446f8694: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:f7bc67956f2920147b5d40d29b801e18090524d35093e690ab310547ac5303df \[598, 695\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A borrower must report a split drumhead or a loose metal fitting within 24 hours of discovering it. \[Ecaf4da2e8b2f3d22446f8694\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecaf4da2e8b2f3d22446f8694: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:f7bc67956f2920147b5d40d29b801e18090524d35093e690ab310547ac5303df \[598, 695\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A borrower must report a split drumhead or loose metal fitting within 24 hours of discovering it.


## gen-held_out-15 / actual

Can I use disinfectant spray to clean a borrowed practice pad?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

No. Practice-pad surfaces are cleaned with the supplied dry microfiber cloth after each use, and students must not spray them with disinfectant. \[E7d148f9f2c2b5953891995e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7d148f9f2c2b5953891995e5: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:aaf325dc69b1b03813c6224bdd91f28d345cad621f3d99a8bf2086d1e85ff1c9 \[2369, 2505\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: Practice-pad surfaces are cleaned with the supplied dry microfiber cloth after each use; students must not spray them with disinfectant.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. Students must not spray borrowed practice pads with disinfectant; clean the surface with the supplied dry microfiber cloth after each use. \[E7d148f9f2c2b5953891995e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7d148f9f2c2b5953891995e5: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:aaf325dc69b1b03813c6224bdd91f28d345cad621f3d99a8bf2086d1e85ff1c9 \[2369, 2505\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: Practice-pad surfaces are cleaned with the supplied dry microfiber cloth after each use; students must not spray them with disinfectant.


## gen-held_out-15 / standard

Can I use disinfectant spray to clean a borrowed practice pad?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

No. Students must not spray a borrowed practice pad with disinfectant; clean its surface with the supplied dry microfiber cloth after each use. \[E7d148f9f2c2b5953891995e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7d148f9f2c2b5953891995e5: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:aaf325dc69b1b03813c6224bdd91f28d345cad621f3d99a8bf2086d1e85ff1c9 \[2369, 2505\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: Practice-pad surfaces are cleaned with the supplied dry microfiber cloth after each use; students must not spray them with disinfectant.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. Students must not spray a borrowed practice pad with disinfectant; clean its surface with the supplied dry microfiber cloth after each use. \[E7d148f9f2c2b5953891995e5\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7d148f9f2c2b5953891995e5: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:aaf325dc69b1b03813c6224bdd91f28d345cad621f3d99a8bf2086d1e85ff1c9 \[2369, 2505\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: Practice-pad surfaces are cleaned with the supplied dry microfiber cloth after each use; students must not spray them with disinfectant.


## gen-held_out-16 / actual

After a safety recall interrupts my loan, what substitute is offered and what normal loan period anchors the remaining time?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

After a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit. \[Ebe8a2a4df2fee71598e8e811\]

The worked example uses a 21-day loan. \[E7b00c616877a8d46ad9e9591\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether 21 days is the normal loan period generally, rather than the period used in the worked example."\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1420, 1570\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: When a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit.
- E7b00c616877a8d46ad9e9591: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:2fe6da53878457d8de90df0239e8b4d45d86e54e8bee24c452fa7ba0574c1724 \[4073, 4165\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A student with a 21-day loan discovers a loose ring on day four and reports it that evening.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

When a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit. \[Ebe8a2a4df2fee71598e8e811\]

The worked example uses a 21-day loan, but it does not establish that 21 days is the normal period for all loans. \[E7b00c616877a8d46ad9e9591\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The generally applicable normal loan period, beyond the 21-day period used in the worked example."\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1420, 1570\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: When a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit.
- E7b00c616877a8d46ad9e9591: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:2fe6da53878457d8de90df0239e8b4d45d86e54e8bee24c452fa7ba0574c1724 \[4073, 4165\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A student with a 21-day loan discovers a loose ring on day four and reports it that evening.


## gen-held_out-16 / standard

After a safety recall interrupts my loan, what substitute is offered and what normal loan period anchors the remaining time?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The repair desk offers a practice pad for the remaining original loan period at no additional deposit; it is not promised to be an identical drum. \[Ebe8a2a4df2fee71598e8e811\]

The normal loan period is 21 calendar days from the signed collection date, with the collection day counted as day zero. \[E8f08ce52d439ce0982dfd518\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1420, 1617\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: When a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit. This offer does not promise an identical drum.
- E8f08ce52d439ce0982dfd518: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk oracle:f1 \[566, 734\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date. The collection day is day zero and the due date is written on the receipt.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

When a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit; it does not promise an identical drum. \[Ebe8a2a4df2fee71598e8e811\]

The normal standard percussion instrument loan lasts 21 calendar days from the signed collection date; the collection day is day zero. \[E8f08ce52d439ce0982dfd518\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1420, 1570\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: When a safety recall interrupts a current loan, the repair desk offers a practice pad for the remaining original loan period at no additional deposit.
- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1571, 1617\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: This offer does not promise an identical drum.
- E8f08ce52d439ce0982dfd518: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk oracle:f1 \[566, 659\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date.
- E8f08ce52d439ce0982dfd518: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk oracle:f1 \[660, 690\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The collection day is day zero


## gen-held_out-17 / actual

For a drum transferred between campuses, what must happen before its student loan time begins?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For an instrument sent between campuses, the receiving clerk must sign the amber transfer card before the loan clock starts. \[E1217da667a3c91f72a63e1cd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1217da667a3c91f72a63e1cd: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:548f0f0a9348d3737786be732ee0c70e395529984cda46b17cfe2ef3e3564ebb \[7138, 7262\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: For an instrument sent between campuses, the receiving clerk must sign the amber transfer card before the loan clock starts.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Before the student loan time begins, the receiving clerk must sign the amber transfer card. \[E1217da667a3c91f72a63e1cd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1217da667a3c91f72a63e1cd: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:548f0f0a9348d3737786be732ee0c70e395529984cda46b17cfe2ef3e3564ebb \[7138, 7262\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: For an instrument sent between campuses, the receiving clerk must sign the amber transfer card before the loan clock starts.


## gen-held_out-17 / standard

For a drum transferred between campuses, what must happen before its student loan time begins?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For an instrument sent between campuses, the receiving clerk must sign the amber transfer card before the loan clock starts. \[E1217da667a3c91f72a63e1cd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1217da667a3c91f72a63e1cd: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:548f0f0a9348d3737786be732ee0c70e395529984cda46b17cfe2ef3e3564ebb \[7138, 7262\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: For an instrument sent between campuses, the receiving clerk must sign the amber transfer card before the loan clock starts.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For an instrument transferred between campuses, the receiving clerk must sign the amber transfer card before the student loan clock starts. \[E1217da667a3c91f72a63e1cd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1217da667a3c91f72a63e1cd: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:548f0f0a9348d3737786be732ee0c70e395529984cda46b17cfe2ef3e3564ebb \[7138, 7262\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: For an instrument sent between campuses, the receiving clerk must sign the amber transfer card before the loan clock starts.


## gen-held_out-18 / actual

How far before departure is the signed residential consent form due?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The signed residential-tour consent form is due to the tour leader 28 calendar days before departure. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[600, 700\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: A signed residential-tour consent form must reach the tour leader 28 calendar days before departure.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The signed residential-tour consent form is due 28 calendar days before departure. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[600, 700\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: A signed residential-tour consent form must reach the tour leader 28 calendar days before departure.


## gen-held_out-18 / standard

How far before departure is the signed residential consent form due?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The signed residential-tour consent form is due 28 calendar days before departure. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[600, 700\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: A signed residential-tour consent form must reach the tour leader 28 calendar days before departure.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The signed residential-tour consent form is due to the tour leader 28 calendar days before departure. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[600, 700\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: A signed residential-tour consent form must reach the tour leader 28 calendar days before departure.


## gen-held_out-19 / actual

What is the main luggage weight limit for the overnight studio trip and is a day bag also allowed?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Each residential-tour participant may bring one main bag weighing at most 12 kilograms. \[E472ef48277a58b2c3f925e18\]

One small day bag is also allowed. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[997, 1107\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Each residential-tour participant may bring one main bag weighing at most 12 kilograms plus one small day bag.
- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[997, 1107\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Each residential-tour participant may bring one main bag weighing at most 12 kilograms plus one small day bag.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For the overnight studio trip, each participant may bring one main bag weighing at most 12 kilograms and one small day bag. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[997, 1107\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Each residential-tour participant may bring one main bag weighing at most 12 kilograms plus one small day bag.


## gen-held_out-19 / standard

What is the main luggage weight limit for the overnight studio trip and is a day bag also allowed?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Each residential-tour participant may bring one main bag weighing at most 12 kilograms. \[E472ef48277a58b2c3f925e18\]

One small day bag is also allowed. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[997, 1107\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Each residential-tour participant may bring one main bag weighing at most 12 kilograms plus one small day bag.
- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[997, 1107\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Each residential-tour participant may bring one main bag weighing at most 12 kilograms plus one small day bag.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Each residential-tour participant may bring one main bag weighing at most 12 kilograms, plus one small day bag. \[E472ef48277a58b2c3f925e18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E472ef48277a58b2c3f925e18: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:2597b4eb21e2d6451028a07dbe591ac2d173a61dcafd5c968a0637cec663c2ac \[997, 1107\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Each residential-tour participant may bring one main bag weighing at most 12 kilograms plus one small day bag.


## gen-held_out-20 / actual

Can a participant enter a friend's sleeping room on the overnight trip without staff?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

No. A participant may enter only their assigned sleeping room unless a staff lead explicitly accompanies the room visit. \[Ec7ef7bbace6fb29aa4ceab79\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec7ef7bbace6fb29aa4ceab79: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:0059b8ae45ccac1667cb3d0619fdea1a723d199495fa9011131a44b88583300b \[2789, 2902\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Participants may enter only their assigned sleeping room unless a staff lead explicitly accompanies a room visit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. A participant may enter only their assigned sleeping room; visiting a friend’s sleeping room is permitted only if a staff lead explicitly accompanies the visit. \[Ec7ef7bbace6fb29aa4ceab79\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec7ef7bbace6fb29aa4ceab79: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:0059b8ae45ccac1667cb3d0619fdea1a723d199495fa9011131a44b88583300b \[2789, 2902\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Participants may enter only their assigned sleeping room unless a staff lead explicitly accompanies a room visit.


## gen-held_out-20 / standard

Can a participant enter a friend's sleeping room on the overnight trip without staff?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A participant may not enter a friend’s sleeping room without a staff lead explicitly accompanying the visit. \[Ec7ef7bbace6fb29aa4ceab79\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec7ef7bbace6fb29aa4ceab79: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:0059b8ae45ccac1667cb3d0619fdea1a723d199495fa9011131a44b88583300b \[2789, 2902\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Participants may enter only their assigned sleeping room unless a staff lead explicitly accompanies a room visit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. A participant may enter only their assigned sleeping room; entering a friend's room is allowed only if a staff lead explicitly accompanies the visit. \[Ec7ef7bbace6fb29aa4ceab79\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ec7ef7bbace6fb29aa4ceab79: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:0059b8ae45ccac1667cb3d0619fdea1a723d199495fa9011131a44b88583300b \[2789, 2902\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: Participants may enter only their assigned sleeping room unless a staff lead explicitly accompanies a room visit.


## gen-held_out-21 / actual

How many duty adults must remain awake until the last residential room check is finished?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

At least two duty adults must remain awake until the final room check is complete. \[E724d019fabacdb3d4ccc9f2a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E724d019fabacdb3d4ccc9f2a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:265ea6f9ec9b0843ccfba1fc0eff0711383124cbf3123fa12af0d87ba6c31784 \[526, 629\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: Residential night cover requires at least two awake duty adults until the final room check is complete.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

At least two duty adults must remain awake until the final room check is complete. \[E724d019fabacdb3d4ccc9f2a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E724d019fabacdb3d4ccc9f2a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:265ea6f9ec9b0843ccfba1fc0eff0711383124cbf3123fa12af0d87ba6c31784 \[526, 629\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: Residential night cover requires at least two awake duty adults until the final room check is complete.


## gen-held_out-21 / standard

How many duty adults must remain awake until the last residential room check is finished?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

At least two duty adults must remain awake until the final room check is complete. \[E724d019fabacdb3d4ccc9f2a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E724d019fabacdb3d4ccc9f2a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:265ea6f9ec9b0843ccfba1fc0eff0711383124cbf3123fa12af0d87ba6c31784 \[526, 629\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: Residential night cover requires at least two awake duty adults until the final room check is complete.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

At least two duty adults must remain awake until the final room check is complete. \[E724d019fabacdb3d4ccc9f2a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E724d019fabacdb3d4ccc9f2a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:265ea6f9ec9b0843ccfba1fc0eff0711383124cbf3123fa12af0d87ba6c31784 \[526, 629\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: Residential night cover requires at least two awake duty adults until the final room check is complete.


## gen-held_out-22 / actual

Who must sign in a participant arriving after the residential evening handover?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The tour leader and the night-support adult must sign in a participant arriving after the evening handover. \[E432704fc5446b0bba49f34a7\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E432704fc5446b0bba49f34a7: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:5bd2106df01b4eefab8472da40f59d40ec9928fc53b2e4794581ce586fea348f \[2299, 2449\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant arriving after the evening handover must be signed in jointly by the tour leader and night-support adult before joining a sleeping room.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A participant arriving after the evening handover must be signed in jointly by the tour leader and the night-support adult before joining a sleeping room. \[E432704fc5446b0bba49f34a7\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E432704fc5446b0bba49f34a7: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:5bd2106df01b4eefab8472da40f59d40ec9928fc53b2e4794581ce586fea348f \[2299, 2449\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant arriving after the evening handover must be signed in jointly by the tour leader and night-support adult before joining a sleeping room.


## gen-held_out-22 / standard

Who must sign in a participant arriving after the residential evening handover?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The tour leader and night-support adult must sign in the participant jointly. \[E432704fc5446b0bba49f34a7\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E432704fc5446b0bba49f34a7: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:5bd2106df01b4eefab8472da40f59d40ec9928fc53b2e4794581ce586fea348f \[2299, 2449\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant arriving after the evening handover must be signed in jointly by the tour leader and night-support adult before joining a sleeping room.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A participant arriving after the residential evening handover must be signed in jointly by the tour leader and the night-support adult before joining a sleeping room. \[E432704fc5446b0bba49f34a7\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E432704fc5446b0bba49f34a7: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:5bd2106df01b4eefab8472da40f59d40ec9928fc53b2e4794581ce586fea348f \[2299, 2449\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant arriving after the evening handover must be signed in jointly by the tour leader and night-support adult before joining a sleeping room.


## gen-held_out-23 / actual

How many business days ahead should a planned sensory adjustment be requested?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A planned sensory adjustment request should reach the support coordinator five business days before the relevant class. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[557, 676\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A planned sensory adjustment request should reach the support coordinator five business days before the relevant class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A planned sensory adjustment request should reach the support coordinator five business days before the relevant class. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[557, 676\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A planned sensory adjustment request should reach the support coordinator five business days before the relevant class.


## gen-held_out-23 / standard

How many business days ahead should a planned sensory adjustment be requested?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A planned sensory adjustment request should reach the support coordinator five business days before the relevant class. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[557, 676\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A planned sensory adjustment request should reach the support coordinator five business days before the relevant class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A planned sensory adjustment request should reach the support coordinator five business days before the relevant class. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[557, 676\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A planned sensory adjustment request should reach the support coordinator five business days before the relevant class.


## gen-held_out-24 / actual

When is a new sensory support plan reviewed if a student misses some classes?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A new sensory support plan is reviewed after the student's first three attended classes; missed classes do not count towards that review point. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[952, 1099\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: An agreed sensory support plan is reviewed after the student's first three attended classes. Missed classes do not count towards this review point.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A new sensory support plan is reviewed after the student's first three attended classes; classes the student misses do not count toward that review point. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[952, 1099\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: An agreed sensory support plan is reviewed after the student's first three attended classes. Missed classes do not count towards this review point.


## gen-held_out-24 / standard

When is a new sensory support plan reviewed if a student misses some classes?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A new sensory support plan is reviewed after the student's first three attended classes; missed classes do not count toward that review point. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[952, 1099\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: An agreed sensory support plan is reviewed after the student's first three attended classes. Missed classes do not count towards this review point.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The new sensory support plan is reviewed after the student's first three attended classes; missed classes do not count toward that review point. \[Ef202d8a8feb0bd2a447e3a45\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef202d8a8feb0bd2a447e3a45: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:e73dedeeb42d50caaace6a11adb15eb361b056890c6860e7da2a980aa9b894c5 \[952, 1099\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: An agreed sensory support plan is reviewed after the student's first three attended classes. Missed classes do not count towards this review point.


## gen-held_out-25 / actual

If a safety recall arrives during my 21-day loan, do I keep the original due date or return it sooner?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A safety recall can override the original due date; follow the repair notice rather than assuming the original due date is guaranteed. \[E790146d5eabc213d1c4036c8\]

In the documented 21-day-loan example, the borrower must meet the next-business-day deadline despite having ordinary loan days remaining. \[Ed98323a46a5e8a73acbf1d98\]

A normal seven-day renewal does not extend the recall deadline. \[E6136fb385534c356e1553e71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E790146d5eabc213d1c4036c8: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2985, 3194\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The repair desk can recall an instrument that develops a safety fault even when a normal renewal would otherwise be available; follow the repair notice rather than assuming the original due date is guaranteed.
- Ed98323a46a5e8a73acbf1d98: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:2fe6da53878457d8de90df0239e8b4d45d86e54e8bee24c452fa7ba0574c1724 \[4222, 4320\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The student must follow the next-business-day deadline even though many ordinary loan days remain.
- E6136fb385534c356e1553e71: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1351, 1418\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The store's normal seven-day renewal does not extend this deadline.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

Do not assume the original due date is guaranteed after a safety recall; follow the repair notice. \[E790146d5eabc213d1c4036c8\]

In the documented 21-day-loan example, the student must meet the next-business-day deadline despite having ordinary loan days remaining. \[Ed98323a46a5e8a73acbf1d98\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The general deadline that applies to every safety recall during a 21-day loan."\]

- E790146d5eabc213d1c4036c8: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2985, 3194\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The repair desk can recall an instrument that develops a safety fault even when a normal renewal would otherwise be available; follow the repair notice rather than assuming the original due date is guaranteed.
- Ed98323a46a5e8a73acbf1d98: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:2fe6da53878457d8de90df0239e8b4d45d86e54e8bee24c452fa7ba0574c1724 \[4222, 4320\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The student must follow the next-business-day deadline even though many ordinary loan days remain.


## gen-held_out-25 / standard

If a safety recall arrives during my 21-day loan, do I keep the original due date or return it sooner?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

If a safety recall arrives during your 21-day loan, you must return the instrument by the end of the next business day; the recall deadline overrides the ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Return the safety-recalled instrument by the end of the next business day; this overrides the ordinary loan due date, so you do not keep the original due date. \[Ebe8a2a4df2fee71598e8e811\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.


## gen-held_out-26 / actual

May I renew a recalled instrument for the usual extra week? State the ordinary renewal condition and the recall deadline.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The usual seven-day renewal is available only if no other student has reserved the asset and the store confirms the renewal before the existing due date. \[E790146d5eabc213d1c4036c8\]

A normal seven-day renewal does not extend the deadline for returning a recalled instrument; the recall deadline given is the next business day. \[E6136fb385534c356e1553e71\] \[Ed98323a46a5e8a73acbf1d98\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E790146d5eabc213d1c4036c8: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2753, 2908\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A loan can be renewed once for seven days if no other student has reserved that asset. Renewal must be confirmed by the store before the existing due date.
- E6136fb385534c356e1553e71: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1351, 1418\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The store's normal seven-day renewal does not extend this deadline.
- Ed98323a46a5e8a73acbf1d98: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:2fe6da53878457d8de90df0239e8b4d45d86e54e8bee24c452fa7ba0574c1724 \[4222, 4320\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The student must follow the next-business-day deadline even though many ordinary loan days remain.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

An ordinary renewal is available once for seven days only if no other student has reserved the asset, and the store confirms the renewal before the existing due date. \[E790146d5eabc213d1c4036c8\]

The ordinary seven-day renewal does not extend the recall deadline. The checklist's worked example says the student must meet a next-business-day deadline, but that example does not establish a general deadline for every recall. \[E6136fb385534c356e1553e71\] \[Ed98323a46a5e8a73acbf1d98\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The applicable recall deadline outside the worked example."\]

- E790146d5eabc213d1c4036c8: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2753, 2908\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A loan can be renewed once for seven days if no other student has reserved that asset. Renewal must be confirmed by the store before the existing due date.
- E6136fb385534c356e1553e71: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1351, 1418\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The store's normal seven-day renewal does not extend this deadline.
- Ed98323a46a5e8a73acbf1d98: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:2fe6da53878457d8de90df0239e8b4d45d86e54e8bee24c452fa7ba0574c1724 \[4222, 4320\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The student must follow the next-business-day deadline even though many ordinary loan days remain.


## gen-held_out-26 / standard

May I renew a recalled instrument for the usual extra week? State the ordinary renewal condition and the recall deadline.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

You cannot use the usual renewal to extend a recalled instrument’s deadline: return it by the end of the next business day, which overrides its ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

Ordinarily, a loan can be renewed once for seven days if no other student has reserved that asset, and the store must confirm the renewal before the existing due date. \[E5feb0fd874b35a5c20feb536\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.
- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1351, 1418\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The store's normal seven-day renewal does not extend this deadline.
- E5feb0fd874b35a5c20feb536: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2753, 2908\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A loan can be renewed once for seven days if no other student has reserved that asset. Renewal must be confirmed by the store before the existing due date.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. The store’s usual seven-day renewal does not extend the deadline for returning a safety-recalled instrument. \[Ebe8a2a4df2fee71598e8e811\]

Ordinarily, a loan may be renewed once for seven days only if no other student has reserved the asset and the store confirms the renewal before the existing due date. A message sent after the desk closes does not itself approve the extension. \[E5feb0fd874b35a5c20feb536\]

A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.
- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[1351, 1418\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The store's normal seven-day renewal does not extend this deadline.
- E5feb0fd874b35a5c20feb536: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2753, 2839\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A loan can be renewed once for seven days if no other student has reserved that asset.
- E5feb0fd874b35a5c20feb536: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2840, 2908\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Renewal must be confirmed by the store before the existing due date.
- E5feb0fd874b35a5c20feb536: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:be61d51af22c9e316cf1474adbc7c71f55c9508d283d2856818c3b7c000298bd \[2909, 2984\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A message sent after the desk closes does not itself approve the extension.
- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.


## gen-held_out-27 / actual

Must all medicine be handed over for the trip, or is a rescue inhaler ever allowed to stay with the participant?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure. \[E92af71c51bb0f7e3e98c3a05\]

A participant may keep a rescue inhaler with them under the narrow exception for a recorded self-carry plan naming the participant, inhaler and trip; this does not permit self-carrying unrelated scheduled tablets. \[Eaab7721d8a7d4a3d3145c903\] \[E92af71c51bb0f7e3e98c3a05\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E92af71c51bb0f7e3e98c3a05: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip. It does not authorize self-carrying unrelated scheduled tablets.
- E92af71c51bb0f7e3e98c3a05: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1722, 1880\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: The night-support notes describe a narrow exception for a recorded self-carried rescue inhaler; ordinary scheduled medication still follows the handover rule.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A rescue inhaler may stay with the participant under the narrow self-carry exception when a recorded plan names the participant, inhaler, and trip; the participant must privately check in with the night-support adult before the evening room check and confirm the inhaler is accessible and the help route is understood. \[Eaab7721d8a7d4a3d3145c903\]

Scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure; the rescue-inhaler exception does not apply to unrelated scheduled tablets. \[E92af71c51bb0f7e3e98c3a05\] \[Eaab7721d8a7d4a3d3145c903\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip.
- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1913, 2036\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant using a self-carried rescue inhaler must check in with the night-support adult before the evening room check.
- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[2037, 2135\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: This is a brief private confirmation that the item is accessible and the help route is understood.
- E92af71c51bb0f7e3e98c3a05: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1635, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: It does not authorize self-carrying unrelated scheduled tablets.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

All scheduled tour medication must be handed to the designated medicines lead at departure in its original labelled packaging. \[E92af71c51bb0f7e3e98c3a05\]

The handbook describes a narrow exception for a recorded self-carried rescue inhaler, but the available text does not establish all of the exception’s governing conditions. \[E92af71c51bb0f7e3e98c3a05\] \[Eaab7721d8a7d4a3d3145c903\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The complete governing conditions for when a rescue inhaler may be self-carried."\]

- E92af71c51bb0f7e3e98c3a05: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- E92af71c51bb0f7e3e98c3a05: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1722, 1816\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: The night-support notes describe a narrow exception for a recorded self-carried rescue inhaler
- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip.
- Eaab7721d8a7d4a3d3145c903: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1913, 2036\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant using a self-carried rescue inhaler must check in with the night-support adult before the evening room check.


## gen-held_out-27 / standard

Must all medicine be handed over for the trip, or is a rescue inhaler ever allowed to stay with the participant?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

All scheduled tour medication must be handed to the designated medicines lead at departure in its original labelled packaging. \[E7f06c4e4dc99fe1f0ea965bf\]

A participant may keep a rescue inhaler with them only if a written self-carry plan naming the participant, inhaler and trip is signed by the guardian and medicines lead; this does not permit carrying unrelated scheduled tablets. \[Eb08666418583bba99dc8c91a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead. The plan names the participant, inhaler and trip. It does not authorize self-carrying unrelated scheduled tablets.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure. \[E7f06c4e4dc99fe1f0ea965bf\]

A participant may keep a rescue inhaler with them only if a written self-carry plan is signed by the guardian and medicines lead and names the participant, inhaler, and trip. The participant must also check in with the night-support adult before the evening room check. \[Eb08666418583bba99dc8c91a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1913, 2036\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant using a self-carried rescue inhaler must check in with the night-support adult before the evening room check.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

A participant may keep a rescue inhaler with them only if there is a written self-carry plan signed by the guardian and medicines lead that names the participant, inhaler, and trip. The participant must also check in privately with the night-support adult before the evening room check to confirm the inhaler is accessible and they understand how to request help. \[Eb08666418583bba99dc8c91a\]

All scheduled tour medication must be handed to the designated medicines lead at departure in its original labelled packaging; the rescue-inhaler exception does not apply to unrelated scheduled tablets. \[E7f06c4e4dc99fe1f0ea965bf\] \[Eb08666418583bba99dc8c91a\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1913, 2036\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant using a self-carried rescue inhaler must check in with the night-support adult before the evening room check.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[2037, 2135\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: This is a brief private confirmation that the item is accessible and the help route is understood.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1635, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: It does not authorize self-carrying unrelated scheduled tablets.


## gen-held_out-28 / actual

May a student keep ear defenders on during class and during an evacuation drill, and what extra condition applies in the drill?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

During ordinary class exercises, a student may wear their own ear defenders after the teacher confirms a visible stop signal and rehearses it with the student before a sequence begins. \[E1a9d8caeda4ea5718be9ca18\]

During an evacuation drill, the student need not remove passive ear defenders merely because the drill starts. \[E56305205fb70ecc2ab8ebac7\]

The extra drill condition is that the visible adult checks the cue and follows the recorded route. \[E56305205fb70ecc2ab8ebac7\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a9d8caeda4ea5718be9ca18: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. The teacher rehearses the signal with the student before a sequence begins.
- E56305205fb70ecc2ab8ebac7: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1630, 1710\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The student need not remove passive ear defenders merely because a drill starts.
- E56305205fb70ecc2ab8ebac7: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1711, 1775\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The visible adult checks the cue and follows the recorded route.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A student may wear their own passive ear defenders during ordinary class exercises if the teacher confirms a visible stop signal and rehearses the signal with the student before a sequence begins. \[E1a9d8caeda4ea5718be9ca18\]

During an evacuation drill, the student need not remove passive ear defenders merely because the drill starts, subject to the ordinary class permission and visible stop signal; the visible adult must check the cue and follow the recorded route. \[E56305205fb70ecc2ab8ebac7\] \[E1a9d8caeda4ea5718be9ca18\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1a9d8caeda4ea5718be9ca18: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. The teacher rehearses the signal with the student before a sequence begins.
- E56305205fb70ecc2ab8ebac7: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1630, 1856\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The student need not remove passive ear defenders merely because a drill starts. The visible adult checks the cue and follows the recorded route. This condition supplements the ordinary class permission and visible stop signal
- E1a9d8caeda4ea5718be9ca18: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. The teacher rehearses the signal with the student before a sequence begins.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

During ordinary class exercises, a student may wear their own ear defenders after the teacher confirms a visible stop signal; the teacher must rehearse the signal with the student before a sequence begins. \[E1a9d8caeda4ea5718be9ca18\]

For an evacuation drill, the room-operation note says the student need not remove passive ear defenders merely because the drill starts, and says the visible adult checks the cue and follows the recorded route. However, the supplied text has an omitted passage in this condition, so it does not establish that these are the complete conditions for keeping the defenders on during a drill. \[E56305205fb70ecc2ab8ebac7\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The omitted governing text within the evacuation-drill condition, needed to determine whether it adds any further condition. "\]

- E1a9d8caeda4ea5718be9ca18: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. The teacher rehearses the signal with the student before a sequence begins.
- E56305205fb70ecc2ab8ebac7: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1630, 1710\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The student need not remove passive ear defenders merely because a drill starts.
- E56305205fb70ecc2ab8ebac7: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1711, 1775\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The visible adult checks the cue and follows the recorded route.


## gen-held_out-28 / standard

May a student keep ear defenders on during class and during an evacuation drill, and what extra condition applies in the drill?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, a student need not remove passive ear defenders merely because the drill starts. \[E8300e8cf9526383805a76a63\]

During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1556\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1630, 1710\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The student need not remove passive ear defenders merely because a drill starts.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1629\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal; the teacher must rehearse that signal with the student before a sequence begins. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, the student need not remove passive ear defenders merely because the drill starts, but must have a named adult within sight who can relay the evacuation cue. The drill condition supplements the ordinary class permission and visible stop signal. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1556\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal.
- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1557, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The teacher rehearses the signal with the student before a sequence begins.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1629\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1630, 1710\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The student need not remove passive ear defenders merely because a drill starts.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1776, 1857\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: This condition supplements the ordinary class permission and visible stop signal;


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

During ordinary class exercises, a student may wear their own ear defenders after the teacher confirms a visible stop signal and rehearses that signal with the student before the sequence begins. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, the student need not remove passive ear defenders merely because the drill starts, but must have a named adult within sight who can relay the evacuation cue; the visible adult checks the cue and follows the recorded route. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. The teacher rehearses the signal with the student before a sequence begins.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1775\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue. The student need not remove passive ear defenders merely because a drill starts. The visible adult checks the cue and follows the recorded route.


## gen-held_out-29 / actual

The two active guest-workshop documents give different deposits. State both amounts and decide which amount is authoritative for charging us.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Guest Artist Office Handbook sets the guest-workshop reservation deposit at $35 per participant. \[E292bfae4bfc9211ec39d7bc3\]

The artist welcome handout sets the guest-workshop reservation deposit at $20 per participant. \[E1622364ff9aa9ab7dc1a1da6\]

Neither amount is established as authoritative for charging: both documents remain current, and no precedence instruction or authority order resolves the disagreement. \[E292bfae4bfc9211ec39d7bc3\] \[E1622364ff9aa9ab7dc1a1da6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["An authoritative decision reconciling the two deposit amounts for charging."\]

- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2209, 2303\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office handbook sets the guest-workshop reservation deposit at 35 dollars per participant.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[955, 1056\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant.
- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2371, 2557\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office is aware that the artist welcome handout prints a different deposit amount for the same workshops; both documents remain current and no precedence instruction has been issued.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[1239, 1372\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Neither document contains an authority order resolving the disagreement, so report both figures and ask the office to reconcile them.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Guest Artist Office Handbook sets the guest-workshop reservation deposit at 35 dollars per participant. \[E292bfae4bfc9211ec39d7bc3\]

The Visiting Artist Welcome and Safeguarding Notes sets the guest-workshop reservation deposit at 20 dollars per participant. \[E1622364ff9aa9ab7dc1a1da6\]

The supplied documents do not establish which amount is authoritative for charging. \[E292bfae4bfc9211ec39d7bc3\] \[E1622364ff9aa9ab7dc1a1da6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which deposit amount is authoritative for charging."\]

- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2209, 2303\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office handbook sets the guest-workshop reservation deposit at 35 dollars per participant.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[955, 1056\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant.
- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2481, 2557\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: both documents remain current and no precedence instruction has been issued.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[1239, 1310\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Neither document contains an authority order resolving the disagreement


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

The Guest Artist Office Handbook sets the guest-workshop reservation deposit at 35 dollars per participant. \[E292bfae4bfc9211ec39d7bc3\]

The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant. \[E1622364ff9aa9ab7dc1a1da6\]

Both documents remain current, and neither establishes which amount takes precedence. \[E292bfae4bfc9211ec39d7bc3\] \[E1622364ff9aa9ab7dc1a1da6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which deposit amount is authoritative for charging."\]

- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2209, 2303\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office handbook sets the guest-workshop reservation deposit at 35 dollars per participant.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[955, 1056\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant.
- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2481, 2557\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: both documents remain current and no precedence instruction has been issued.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[1239, 1310\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Neither document contains an authority order resolving the disagreement


## gen-held_out-29 / standard

The two active guest-workshop documents give different deposits. State both amounts and decide which amount is authoritative for charging us.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The office handbook states a guest-workshop reservation deposit of 35 dollars per participant. \[E292bfae4bfc9211ec39d7bc3\]

The artist welcome handout states a guest-workshop reservation deposit of 20 dollars per participant. \[E1622364ff9aa9ab7dc1a1da6\]

The documents do not establish which deposit amount is authoritative for charging; the handbook says no precedence instruction has been issued and calls for a human decision. \[E292bfae4bfc9211ec39d7bc3\] \[E1622364ff9aa9ab7dc1a1da6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["An authoritative decision identifying which deposit amount to charge."\]

- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2209, 2303\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office handbook sets the guest-workshop reservation deposit at 35 dollars per participant.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[955, 1056\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant.
- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2371, 2679\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office is aware that the artist welcome handout prints a different deposit amount for the same workshops; both documents remain current and no precedence instruction has been issued. Staff must surface the discrepancy for a human decision rather than choosing the larger, smaller or newer-looking figure.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[1239, 1372\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Neither document contains an authority order resolving the disagreement, so report both figures and ask the office to reconcile them.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Guest Artist Office Handbook states a guest-workshop reservation deposit of $35 per participant. \[E292bfae4bfc9211ec39d7bc3\]

The Visiting Artist Welcome and Safeguarding Notes states a guest-workshop reservation deposit of $20 per participant. \[E1622364ff9aa9ab7dc1a1da6\]

The supplied documents do not establish which amount is authoritative for charging; the handbook says no precedence instruction has been issued, and the welcome notes say neither document contains an authority order resolving the disagreement. \[E292bfae4bfc9211ec39d7bc3\] \[E1622364ff9aa9ab7dc1a1da6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["A decision on which deposit amount governs charging."\]

- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2209, 2303\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office handbook sets the guest-workshop reservation deposit at 35 dollars per participant.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[955, 1056\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant.
- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2481, 2557\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: both documents remain current and no precedence instruction has been issued.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[1239, 1310\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Neither document contains an authority order resolving the disagreement


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

The Guest Artist Office Handbook sets the guest-workshop reservation deposit at $35 per participant. \[E292bfae4bfc9211ec39d7bc3\]

The artist welcome handout sets the guest-workshop reservation deposit at $20 per participant. \[E1622364ff9aa9ab7dc1a1da6\]

Both documents remain current, and the evidence does not establish which amount is authoritative for charging. \[E292bfae4bfc9211ec39d7bc3\] \[E1622364ff9aa9ab7dc1a1da6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which deposit amount is authoritative for charging."\]

- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2209, 2303\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: The office handbook sets the guest-workshop reservation deposit at 35 dollars per participant.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[955, 1056\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: The artist welcome handout sets the guest-workshop reservation deposit at 20 dollars per participant.
- E292bfae4bfc9211ec39d7bc3: 47ffc3a1-30b9-5d00-bb12-d08f15c177ac revision 1 chunk parent:faeec2086c64abf4029f36d562099853411be55a4ba66b3aaad97de3bedeb50c \[2481, 2557\); valid 2027-01-01 through 2027-12-31; SHA-256 c2b5c4a5bc052c26e5ee34150a6f55ce7c47bb786bba1f9511cdb76f26678d8b; quote: both documents remain current and no precedence instruction has been issued.
- E1622364ff9aa9ab7dc1a1da6: 4ee1c78d-5631-5e96-9085-a3f68621d72f revision 1 chunk parent:972a2d2b90640273b52be1ec48f01a2ecfa4e8abacfd65b5b90d0d930af09971 \[1239, 1310\); valid 2027-01-01 through 2027-12-31; SHA-256 53f728d0cf9654d9398f31550aa79a045386e940249de6808797a24adc5380ff; quote: Neither document contains an authority order resolving the disagreement


## gen-held_out-30 / actual

The current store and repair documents disagree about the hand-drum deposit. State both amounts and tell me definitively which one I must pay.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The store procedure states a refundable deposit of 45 dollars for a hand-drum kit. \[Ed91f0b11f10b8e06071f7f42\]

The repair checklist states a refundable deposit of 30 dollars for a hand-drum kit. \[Ed5b1e23c405ee5f3cfa3bb77\]

The documents do not establish definitively which amount must be paid, because both instructions are active and neither declares precedence. \[Ed91f0b11f10b8e06071f7f42\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which deposit amount is authoritative for the hand-drum kit."\]

- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1423, 1503\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The store procedure requires a 45 dollar refundable deposit for a hand-drum kit.
- Ed5b1e23c405ee5f3cfa3bb77: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:0773673aa1cdcc4c5df5dd65c7ea2e85731d6549fb3ca01bd4c02fb6a1816994 \[1885, 1966\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The repair checklist requires a 30 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1595, 1656\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Both instructions are active and neither declares precedence.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The repair checklist states a refundable hand-drum kit deposit of $30. \[Ed5b1e23c405ee5f3cfa3bb77\]

The store procedure states a refundable hand-drum kit deposit of $45. \[Ed91f0b11f10b8e06071f7f42\]

The documents do not establish which amount you must pay: both instructions are active, neither declares precedence, and the store procedure says to preserve both amounts and request clarification. \[Ed91f0b11f10b8e06071f7f42\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which deposit amount is authoritative for the hand-drum kit."\]

- Ed5b1e23c405ee5f3cfa3bb77: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:0773673aa1cdcc4c5df5dd65c7ea2e85731d6549fb3ca01bd4c02fb6a1816994 \[1885, 1966\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The repair checklist requires a 30 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1423, 1503\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The store procedure requires a 45 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1595, 1656\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Both instructions are active and neither declares precedence.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1657, 1728\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Staff must preserve both amounts in an answer and request clarification


## gen-held_out-30 / standard

The current store and repair documents disagree about the hand-drum deposit. State both amounts and tell me definitively which one I must pay.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The repair checklist requires a 30 dollar refundable deposit for a hand-drum kit. \[Ed5b1e23c405ee5f3cfa3bb77\]

The store procedure requires a 45 dollar refundable deposit for a hand-drum kit. \[Ed91f0b11f10b8e06071f7f42\]

The documents do not establish which amount you must pay: both instructions are active, neither declares precedence, and the store procedure says to request clarification. \[Ed91f0b11f10b8e06071f7f42\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which amount is authoritative for the hand-drum deposit."\]

- Ed5b1e23c405ee5f3cfa3bb77: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:0773673aa1cdcc4c5df5dd65c7ea2e85731d6549fb3ca01bd4c02fb6a1816994 \[1885, 1966\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The repair checklist requires a 30 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1423, 1503\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The store procedure requires a 45 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1595, 1777\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Both instructions are active and neither declares precedence. Staff must preserve both amounts in an answer and request clarification; this is not permission to collect two deposits.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The repair checklist states that the refundable deposit for a hand-drum kit is 30 dollars. \[Ed5b1e23c405ee5f3cfa3bb77\]

The store procedure states that the refundable deposit for a hand-drum kit is 45 dollars. \[Ed91f0b11f10b8e06071f7f42\]

The documents do not establish which amount takes precedence: the store procedure says both instructions are active and neither declares precedence, and the repair checklist says it has not been announced to override the store procedure. \[Ed91f0b11f10b8e06071f7f42\] \[Ed5b1e23c405ee5f3cfa3bb77\]

The store procedure says staff should preserve both amounts and request clarification; it does not establish a definitive amount to pay. \[Ed91f0b11f10b8e06071f7f42\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which deposit amount is authoritative for payment."\]

- Ed5b1e23c405ee5f3cfa3bb77: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:0773673aa1cdcc4c5df5dd65c7ea2e85731d6549fb3ca01bd4c02fb6a1816994 \[1885, 1966\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The repair checklist requires a 30 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1423, 1503\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: The store procedure requires a 45 dollar refundable deposit for a hand-drum kit.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1595, 1656\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Both instructions are active and neither declares precedence.
- Ed5b1e23c405ee5f3cfa3bb77: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:0773673aa1cdcc4c5df5dd65c7ea2e85731d6549fb3ca01bd4c02fb6a1816994 \[2048, 2131\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: The repair desk has not announced that its checklist overrides the store procedure.
- Ed91f0b11f10b8e06071f7f42: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk parent:c13af9756c7e11390f19f80260d3bb02925c903a6b7f0c16cdebd8a1eecfb917 \[1657, 1729\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: Staff must preserve both amounts in an answer and request clarification;


## gen-held_out-31 / actual

The two active quiet-room documents give different check-in intervals. Explain the conflicting intervals and choose the authoritative one without consulting anyone.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The sensory planning guide permits a quiet-room break of up to 15 minutes before a teacher check-in. \[E49b21f15e7dcc9948c9d84e3\]

The room-operation notes require a teacher check-in after ten minutes of an ordinary quiet-room break. \[E819f85be3f05768c7eb977eb\]

The supplied documents do not establish which interval is authoritative: the guide says neither current document establishes a precedence rule, and the operation notes do not declare that operations automatically outrank planning. \[E49b21f15e7dcc9948c9d84e3\] \[E819f85be3f05768c7eb977eb\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which check-in interval is authoritative."\]

- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2299, 2399\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The sensory planning guide permits a quiet-room break of up to 15 minutes before a teacher check-in.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[976, 1078\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The room-operation notes require a teacher check-in after ten minutes of an ordinary quiet-room break.
- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2494, 2549\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: Neither current document establishes a precedence rule.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[1162, 1236\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: These notes do not declare that operations automatically outrank planning.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Sensory Support Planning Guide allows up to 15 minutes before a teacher check-in. \[E49b21f15e7dcc9948c9d84e3\]

The Quiet Room Operation and Emergency Notes require a teacher check-in after ten minutes of an ordinary quiet-room break. \[E819f85be3f05768c7eb977eb\]

The evidence does not establish which interval is authoritative, so it does not support choosing one over the other. \[E49b21f15e7dcc9948c9d84e3\] \[E819f85be3f05768c7eb977eb\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["An authoritative precedence rule between the two documents."\]

- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2326, 2398\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: permits a quiet-room break of up to 15 minutes before a teacher check-in
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[1001, 1077\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: require a teacher check-in after ten minutes of an ordinary quiet-room break
- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2494, 2549\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: Neither current document establishes a precedence rule.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[1162, 1236\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: These notes do not declare that operations automatically outrank planning.


## gen-held_out-31 / standard

The two active quiet-room documents give different check-in intervals. Explain the conflicting intervals and choose the authoritative one without consulting anyone.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The sensory planning guide permits a quiet-room break of up to 15 minutes before a teacher check-in. \[E49b21f15e7dcc9948c9d84e3\]

The room-operation notes require a teacher check-in after ten minutes of an ordinary quiet-room break. \[E819f85be3f05768c7eb977eb\]

Neither document establishes which interval is authoritative. \[E49b21f15e7dcc9948c9d84e3\] \[E819f85be3f05768c7eb977eb\]

The operation notes say to preserve the disagreement and obtain clarification from the support coordinator. \[E819f85be3f05768c7eb977eb\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which interval the studio has designated as authoritative."\]

- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2299, 2399\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The sensory planning guide permits a quiet-room break of up to 15 minutes before a teacher check-in.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[976, 1078\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The room-operation notes require a teacher check-in after ten minutes of an ordinary quiet-room break.
- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2494, 2549\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: Neither current document establishes a precedence rule.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[1162, 1236\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: These notes do not declare that operations automatically outrank planning.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[1237, 1330\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: Staff should preserve the disagreement and obtain clarification from the support coordinator.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Sensory Support Planning Guide gives an interval of up to 15 minutes before a teacher check-in for a quiet-room break. \[E49b21f15e7dcc9948c9d84e3\]

The Quiet Room Operation and Emergency Notes require a teacher check-in after ten minutes of an ordinary quiet-room break. \[E819f85be3f05768c7eb977eb\]

The evidence does not establish which interval is authoritative: neither document establishes precedence, and the operation notes do not declare that they automatically outrank the planning guide. \[E49b21f15e7dcc9948c9d84e3\] \[E819f85be3f05768c7eb977eb\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which interval is authoritative."\]

- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2299, 2399\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The sensory planning guide permits a quiet-room break of up to 15 minutes before a teacher check-in.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[976, 1078\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: The room-operation notes require a teacher check-in after ten minutes of an ordinary quiet-room break.
- E49b21f15e7dcc9948c9d84e3: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:c0b308614f956eaf2355b6830914fc26928c1e02a16e3a163213aca6f3c8aecd \[2494, 2549\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: Neither current document establishes a precedence rule.
- E819f85be3f05768c7eb977eb: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:ce20df9778985525adf1e1c9152fb9b3c48b3526f87f2c7e374f29b5dc9fd9a9 \[1162, 1236\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: These notes do not declare that operations automatically outrank planning.


## gen-held_out-32 / actual

What annual royalty percentage does the studio pay a visiting choreographer for repeating their routine?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The annual royalty percentage paid to a visiting choreographer for repeating their routine."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The annual royalty percentage paid for repeating a visiting choreographer’s routine."\]



## gen-held_out-32 / standard

What annual royalty percentage does the studio pay a visiting choreographer for repeating their routine?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The annual royalty percentage paid for repeating a visiting choreographer’s routine is not stated in the supplied evidence."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The annual royalty percentage paid for repeating a visiting choreographer’s routine."\]



## gen-held_out-33 / actual

What is the fixed late-return fine per day for a borrowed hand drum?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The supplied evidence does not specify a fixed late-return fine per day for a borrowed hand drum."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The fixed late-return fine per day for a borrowed hand drum."\]



## gen-held_out-33 / standard

What is the fixed late-return fine per day for a borrowed hand drum?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["Whether a fixed late-return fine per day applies to a borrowed hand drum, and its amount."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-held_out-34 / actual

What is the sensory support coordinator's professional registration number?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The sensory support coordinator's professional registration number."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-held_out-34 / standard

What is the sensory support coordinator's professional registration number?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The sensory support coordinator's professional registration number is not provided in the supplied evidence."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The sensory support coordinator's professional registration number."\]



## gen-held_out-35 / actual

What deposit is required for a visiting artist workshop in June 2029?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-held_out-35 / standard

What deposit is required for a visiting artist workshop in June 2029?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-held_out-36 / actual

How long may I borrow a hand drum in June 2029?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-held_out-36 / standard

How long may I borrow a hand drum in June 2029?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-held_out-37 / actual

When must I return this loan instrument? I have not said whether it is subject to a safety recall or when I collected it.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

If the instrument is subject to a safety recall, it must be returned by the end of the next business day, overriding its ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether this instrument is subject to a safety recall.", "The instrument’s recorded ordinary due date, or the loan details needed to establish it."\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

If this instrument is subject to a safety recall, it must be returned by the end of the next business day; that deadline overrides its ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether the instrument is subject to a safety recall. If it is not recalled, the ordinary due date shown on the loan receipt is needed to determine when it must be returned."\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.


## gen-held_out-37 / standard

When must I return this loan instrument? I have not said whether it is subject to a safety recall or when I collected it.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I need more details before I can confirm an answer.

If the instrument is subject to a safety recall, it must be returned by the end of the next business day, overriding its ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

For a standard loan without an overriding recall deadline, the loan lasts 21 calendar days from the signed collection date; the collection day is day zero, and the due date is written on the receipt. \[E8f08ce52d439ce0982dfd518\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether this instrument is subject to a safety recall.", "The signed collection date or the due date written on the receipt."\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.
- E8f08ce52d439ce0982dfd518: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk oracle:f1 \[566, 734\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date. The collection day is day zero and the due date is written on the receipt.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

If the instrument is subject to a safety recall, it must be returned by the end of the next business day, overriding its ordinary loan due date. \[Ebe8a2a4df2fee71598e8e811\]

For a standard loan that is not subject to a recall deadline, the loan lasts 21 calendar days from the signed collection date, and the due date is written on the receipt. \[E8f08ce52d439ce0982dfd518\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether the instrument is subject to a safety recall.", "The receipt's due date or, if that is unavailable, the signed collection date."\]

- Ebe8a2a4df2fee71598e8e811: 1e20f5fe-28c5-55c1-aa91-988a2e7a2277 revision 1 chunk parent:99f6dcbd04ef589ddc816f8f13b744e200c3ff1ac8893680030a52eeb5522836 \[992, 1113\); valid 2027-01-01 through 2027-12-31; SHA-256 1a0391ba007835fbf18c38d423b7766977d50b8f2fae063a053ec557b1bbc9a3; quote: A safety-recalled instrument must be returned by the end of the next business day, overriding its ordinary loan due date.
- E8f08ce52d439ce0982dfd518: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk oracle:f1 \[566, 659\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: A standard percussion instrument loan lasts 21 calendar days from the signed collection date.
- E8f08ce52d439ce0982dfd518: ec686257-3e33-573a-91e2-aa7314089014 revision 1 chunk oracle:f1 \[695, 734\); valid 2027-01-01 through 2027-12-31; SHA-256 a41b41e7578577b751a3db1a580338c04ac7ae4b1fe256907cea455e1c96f230; quote: the due date is written on the receipt.


## gen-held_out-38 / actual

May I keep my medicine with me on the residential trip? I have not said which medicine it is or whether I have a signed self-carry plan.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

You may keep a rescue inhaler with you only if there is a written self-carry plan signed by your guardian and the medicines lead, naming you, the inhaler and the trip. \[Eb08666418583bba99dc8c91a\]

Scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure. \[E7f06c4e4dc99fe1f0ea965bf\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Which medicine you mean and whether it is a rescue inhaler or scheduled tour medication.", "Whether you have a written self-carry plan signed by your guardian and the medicines lead that names you, the inhaler and the trip."\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead. The plan names the participant, inhaler and trip.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I need more details before I can confirm an answer.

A participant may keep a rescue inhaler on their person only if there is a written self-carry plan signed by the guardian and medicines lead that names the participant, inhaler, and trip. \[Eb08666418583bba99dc8c91a\]

Scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging; a rescue-inhaler self-carry exception does not authorize self-carrying unrelated scheduled tablets. \[E7f06c4e4dc99fe1f0ea965bf\] \[Eb08666418583bba99dc8c91a\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["What medicine do you mean?", "If it is a rescue inhaler, is there a written self-carry plan signed by the guardian and medicines lead that names you, the inhaler, and this trip?"\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1635, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: It does not authorize self-carrying unrelated scheduled tablets.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I need more details before I can confirm an answer.

A participant may keep a rescue inhaler with them only if a written self-carry plan is signed by both the guardian and medicines lead, and the plan names the participant, inhaler, and trip. \[Eb08666418583bba99dc8c91a\]

Scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging; the rescue-inhaler exception does not apply to ordinary scheduled medication. \[E7f06c4e4dc99fe1f0ea965bf\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Which medicine you mean.", "Whether there is a written self-carry plan signed by the guardian and medicines lead that names you, the medicine, and this trip."\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead. The plan names the participant, inhaler and trip.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1722, 1880\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: The night-support notes describe a narrow exception for a recorded self-carried rescue inhaler; ordinary scheduled medication still follows the handover rule.


## gen-held_out-38 / standard

May I keep my medicine with me on the residential trip? I have not said which medicine it is or whether I have a signed self-carry plan.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

You may keep a rescue inhaler with you only if there is a written self-carry plan signed by your guardian and the medicines lead that names you, the inhaler, and the trip. \[Eb08666418583bba99dc8c91a\]

Scheduled tour medication must be handed to the designated medicines lead at departure in its original labelled packaging. \[E7f06c4e4dc99fe1f0ea965bf\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Which medicine you mean.", "Whether you have a written self-carry plan signed by your guardian and the medicines lead that names you, the medicine, and this trip."\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead. The plan names the participant, inhaler and trip.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I need more details before I can confirm an answer.

A participant may keep a rescue inhaler with them only if a written self-carry plan is signed by the guardian and medicines lead and names the participant, inhaler, and trip. This exception does not authorize carrying unrelated scheduled tablets. \[Eb08666418583bba99dc8c91a\]

All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure. \[E7f06c4e4dc99fe1f0ea965bf\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Which medicine you mean.", "Whether there is a written self-carry plan signed by the guardian and medicines lead that names you, the medicine, and this trip."\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1585, 1634\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: The plan names the participant, inhaler and trip.
- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1635, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: It does not authorize self-carrying unrelated scheduled tablets.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I need more details before I can confirm an answer.

A participant may keep a rescue inhaler on their person only if a written self-carry plan is signed by the guardian and medicines lead and names the participant, inhaler, and trip. This exception does not authorize self-carrying unrelated scheduled tablets. \[Eb08666418583bba99dc8c91a\]

Scheduled tour medication must be handed to the designated medicines lead at departure in its original labelled packaging. \[E7f06c4e4dc99fe1f0ea965bf\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Which medicine you mean.", "Whether a written self-carry plan for that medicine is signed by the guardian and medicines lead and names you, the medicine, and this trip."\]

- Eb08666418583bba99dc8c91a: 84967edf-cd1e-5cb3-b477-635f6925d4e3 revision 1 chunk parent:0b37167db848421c39270db0cb78c62acf739f2869ada925cc100de1b03b8d55 \[1447, 1699\); valid 2027-01-01 through 2027-12-31; SHA-256 42ffb9148449c8126c296e377fff6931d1af9c6b8acd9da7d061025347dfb8d2; quote: A participant may keep a rescue inhaler on their person only when a written self-carry plan is signed by the guardian and medicines lead. The plan names the participant, inhaler and trip. It does not authorize self-carrying unrelated scheduled tablets.
- E7f06c4e4dc99fe1f0ea965bf: 08a65785-f11f-5b68-ba69-f658c9a2f9b0 revision 1 chunk parent:db19ce8ebfce859b2258891164818847b87fb5797bcf593868ef96dc6e845f09 \[1458, 1584\); valid 2027-01-01 through 2027-12-31; SHA-256 b9dcc8d8d10be662012012c0230c2f2cd15e7cf976659e780374f3ef2c20ac98; quote: All scheduled tour medication must be handed to the designated medicines lead in its original labelled packaging at departure.


## gen-held_out-39 / actual

Is loan drum asset DR-204 currently available for me, and has anyone already reserved that specific instrument?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Current availability of asset DR-204 for you.", "Whether asset DR-204 has already been reserved."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Current availability and reservation status of asset DR-204."\]



## gen-held_out-39 / standard

Is loan drum asset DR-204 currently available for me, and has anyone already reserved that specific instrument?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Current availability of asset DR-204", "Whether asset DR-204 has already been reserved"\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Current inventory and reservation records for asset DR-204 are needed to determine its availability and whether it has been reserved.", "Your applicable loan request details are needed to determine whether it is available for you."\]



## gen-held_out-40 / actual

What visible support is required for ordinary ear-defender use and what adult support must be in sight during a drill?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

During ordinary class exercises, a student may wear their own ear defenders after the teacher confirms a visible stop signal and rehearses that signal with the student before a sequence begins. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, a named adult who can relay the evacuation cue must be within sight of the student using ear defenders. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1556\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal.
- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1557, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The teacher rehearses the signal with the student before a sequence begins.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1629\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For ordinary class exercises, a student may wear their own ear defenders after the teacher confirms a visible stop signal and rehearses it with the student before a sequence begins. Permission for passive ear defenders does not automatically cover headphones playing private music. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1556\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal.
- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1557, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The teacher rehearses the signal with the student before a sequence begins.
- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1788, 1891\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: Headphones playing private music are not automatically covered by permission for passive ear defenders.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1629\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue.


## gen-held_out-40 / standard

What visible support is required for ordinary ear-defender use and what adult support must be in sight during a drill?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For ordinary class exercises, the student may wear their own ear defenders after the teacher confirms a visible stop signal and rehearses it with the student before the sequence begins. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal. The teacher rehearses the signal with the student before a sequence begins.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1629\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For ordinary class exercises, a student may use their own ear defenders after the teacher confirms a visible stop signal and rehearses that signal with the student before a sequence begins. \[Eed2e83ddb73abfba27ce8901\]

During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue. \[E8300e8cf9526383805a76a63\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1432, 1556\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: A student may wear their own ear defenders during ordinary class exercises after the teacher confirms a visible stop signal.
- Eed2e83ddb73abfba27ce8901: 5a52afdd-37c8-50bb-9ee0-6818bd7248d2 revision 1 chunk parent:9e01a6442dd44f4717e8102958eebcd3e785fc8c5de249f63d35ebda09f48170 \[1557, 1632\); valid 2027-01-01 through 2027-12-31; SHA-256 fb71951b316eb8497297c92ef357e4ee4384ef67447f5847aa72f816b6f74894; quote: The teacher rehearses the signal with the student before a sequence begins.
- E8300e8cf9526383805a76a63: 96a11982-b142-5734-8b7f-7418e1a65970 revision 1 chunk parent:805089621cd6161aac0a09ec84068f39ebe92622d4002d175d42efcfb3cc0b13 \[1501, 1629\); valid 2027-01-01 through 2027-12-31; SHA-256 d78f15e21b66fb6a24033d4167d0a25e433541fb074ac73276b8e8938206fc57; quote: During an evacuation drill, a student using ear defenders must have a named adult within sight who can relay the evacuation cue.


## gen-tuning-01 / actual

In 2026, how far ahead did a family have to report an ordinary absence for a replacement lesson?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

In 2026, an ordinary absence had to be reported at least 12 hours before class to earn a makeup credit. \[Ea92b562f543edeb612bd0309\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether earning a makeup credit guaranteed or provided a replacement lesson or booked place."\]

- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[321, 422\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: In 2026, an ordinary absence must be reported at least 12 hours before class to earn a makeup credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2026, an ordinary absence had to be reported at least 12 hours before class to earn a makeup credit. \[Ea92b562f543edeb612bd0309\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[321, 422\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: In 2026, an ordinary absence must be reported at least 12 hours before class to earn a makeup credit.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

In 2026, an ordinary absence had to be reported at least 12 hours before class to earn a makeup credit. \[Ea92b562f543edeb612bd0309\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[321, 422\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: In 2026, an ordinary absence must be reported at least 12 hours before class to earn a makeup credit.


## gen-tuning-01 / standard

In 2026, how far ahead did a family have to report an ordinary absence for a replacement lesson?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2026, an ordinary absence had to be reported at least 12 hours before class to earn a makeup credit. \[Ea92b562f543edeb612bd0309\]

That notice requirement does not itself establish that a replacement lesson place was available or booked. \[Ea92b562f543edeb612bd0309\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[321, 422\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: In 2026, an ordinary absence must be reported at least 12 hours before class to earn a makeup credit.
- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[424, 634\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A promised replacement lesson is different from a booked place. Staff first establish the policy year and record the original missed session. A friendly acknowledgement does not prove that a place is available.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2026, an ordinary absence had to be reported at least 12 hours before class to earn a makeup credit. \[Ea92b562f543edeb612bd0309\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[321, 422\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: In 2026, an ordinary absence must be reported at least 12 hours before class to earn a makeup credit.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

In 2026, an ordinary absence had to be reported at least 12 hours before class to earn a makeup credit. \[Ea92b562f543edeb612bd0309\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea92b562f543edeb612bd0309: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:9096e32bffce6f18a703b680d29e715bb9de2839ff1888dc3b7eb7256e7c4344 \[321, 422\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: In 2026, an ordinary absence must be reported at least 12 hours before class to earn a makeup credit.


## gen-tuning-02 / actual

How long did a 2026 replacement-class credit remain usable?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A makeup credit issued under the 2026 attendance rules expired 30 calendar days after the missed class. \[Ebccacad9af7433bc652df8cf\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebccacad9af7433bc652df8cf: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:c64570f290e446ff5f64d4825937a973f93eef702b9343fd890b885a65a5eb73 \[1645, 1748\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A makeup credit issued under the 2026 attendance rules expires 30 calendar days after the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A 2026 makeup credit remained usable for 30 calendar days after the missed class, after which it expired. \[Ebccacad9af7433bc652df8cf\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebccacad9af7433bc652df8cf: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:c64570f290e446ff5f64d4825937a973f93eef702b9343fd890b885a65a5eb73 \[1645, 1748\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A makeup credit issued under the 2026 attendance rules expires 30 calendar days after the missed class.


## gen-tuning-02 / standard

How long did a 2026 replacement-class credit remain usable?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A 2026 makeup credit remained usable for 30 calendar days after the missed class. \[Ebccacad9af7433bc652df8cf\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebccacad9af7433bc652df8cf: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:c64570f290e446ff5f64d4825937a973f93eef702b9343fd890b885a65a5eb73 \[1645, 1748\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A makeup credit issued under the 2026 attendance rules expires 30 calendar days after the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A 2026 makeup credit remained usable for 30 calendar days after the missed class. \[Ebccacad9af7433bc652df8cf\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ebccacad9af7433bc652df8cf: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:c64570f290e446ff5f64d4825937a973f93eef702b9343fd890b885a65a5eb73 \[1645, 1748\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A makeup credit issued under the 2026 attendance rules expires 30 calendar days after the missed class.


## gen-tuning-03 / actual

What was the deadline for providing medical evidence after a missed lesson in 2026?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2026, a doctor’s certificate for the medical exception had to be submitted within five calendar days of the missed class. \[E5d0b88bf0709aea65e9cfd33\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5d0b88bf0709aea65e9cfd33: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:621a06f65384a8855c81795ba57e272d556a6458a031972e50596ccf98645a5c \[2971, 3085\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The 2026 medical exception accepts a doctor’s certificate submitted within five calendar days of the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2026, medical evidence for a missed class had to be submitted within five calendar days of the missed class; the specified evidence was a doctor’s certificate. \[E5d0b88bf0709aea65e9cfd33\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5d0b88bf0709aea65e9cfd33: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:621a06f65384a8855c81795ba57e272d556a6458a031972e50596ccf98645a5c \[2971, 3085\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The 2026 medical exception accepts a doctor’s certificate submitted within five calendar days of the missed class.


## gen-tuning-03 / standard

What was the deadline for providing medical evidence after a missed lesson in 2026?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2026, the medical exception accepted a doctor’s certificate submitted within five calendar days of the missed class. \[E5d0b88bf0709aea65e9cfd33\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5d0b88bf0709aea65e9cfd33: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:621a06f65384a8855c81795ba57e272d556a6458a031972e50596ccf98645a5c \[2971, 3085\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The 2026 medical exception accepts a doctor’s certificate submitted within five calendar days of the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2026, a doctor’s certificate had to be submitted within five calendar days of the missed class. \[E5d0b88bf0709aea65e9cfd33\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5d0b88bf0709aea65e9cfd33: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:621a06f65384a8855c81795ba57e272d556a6458a031972e50596ccf98645a5c \[2971, 3085\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The 2026 medical exception accepts a doctor’s certificate submitted within five calendar days of the missed class.


## gen-tuning-04 / actual

Could a sibling use another child’s absence credit under the archived attendance policy?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

No. Under the archived 2026 attendance policy, an absence credit belongs to the absent student and cannot be transferred to a sibling. \[E79143af2dc78e3e6f3b6dbb8\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E79143af2dc78e3e6f3b6dbb8: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:5f8503ac6bdd25ea78ab3081909073bc45e9b9b387d0ce41f98f2640f4053da8 \[4319, 4420\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A 2026 attendance makeup credit belongs to the absent student and cannot be transferred to a sibling.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. Under the archived 2026 attendance policy, a makeup credit belongs to the student who was absent and cannot be transferred to a sibling. \[E79143af2dc78e3e6f3b6dbb8\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E79143af2dc78e3e6f3b6dbb8: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:5f8503ac6bdd25ea78ab3081909073bc45e9b9b387d0ce41f98f2640f4053da8 \[4319, 4420\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A 2026 attendance makeup credit belongs to the absent student and cannot be transferred to a sibling.


## gen-tuning-04 / standard

Could a sibling use another child’s absence credit under the archived attendance policy?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Under the archived 2026 attendance policy, an absence credit belongs to the absent student and cannot be transferred to a sibling. \[E79143af2dc78e3e6f3b6dbb8\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E79143af2dc78e3e6f3b6dbb8: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:5f8503ac6bdd25ea78ab3081909073bc45e9b9b387d0ce41f98f2640f4053da8 \[4319, 4420\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A 2026 attendance makeup credit belongs to the absent student and cannot be transferred to a sibling.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. Under the archived 2026 attendance policy, a makeup credit belongs to the student who was absent and cannot be transferred to a sibling. \[E79143af2dc78e3e6f3b6dbb8\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E79143af2dc78e3e6f3b6dbb8: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:5f8503ac6bdd25ea78ab3081909073bc45e9b9b387d0ce41f98f2640f4053da8 \[4319, 4420\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: A 2026 attendance makeup credit belongs to the absent student and cannot be transferred to a sibling.


## gen-tuning-05 / actual

Which timestamp must the year-end 2026 attendance audit preserve?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The year-end 2026 attendance audit must preserve the original absence timestamp, not a later teacher reply timestamp. \[Ed0c4a4a07906d9f80ad2102f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ed0c4a4a07906d9f80ad2102f: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:8fb8af548a8ab99c5ffa563a05b57b07c474a901eabe7353a84d5e4573451223 \[7554, 7673\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The final 2026 attendance audit must retain the original absence timestamp rather than a later teacher reply timestamp.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The year-end 2026 attendance audit must preserve the original absence timestamp, not a later teacher reply timestamp. \[Ed0c4a4a07906d9f80ad2102f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ed0c4a4a07906d9f80ad2102f: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:8fb8af548a8ab99c5ffa563a05b57b07c474a901eabe7353a84d5e4573451223 \[7554, 7673\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The final 2026 attendance audit must retain the original absence timestamp rather than a later teacher reply timestamp.


## gen-tuning-05 / standard

Which timestamp must the year-end 2026 attendance audit preserve?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The year-end 2026 attendance audit must preserve the original absence timestamp, not a later teacher reply timestamp. \[Ed0c4a4a07906d9f80ad2102f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ed0c4a4a07906d9f80ad2102f: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:8fb8af548a8ab99c5ffa563a05b57b07c474a901eabe7353a84d5e4573451223 \[7554, 7673\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The final 2026 attendance audit must retain the original absence timestamp rather than a later teacher reply timestamp.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The year-end 2026 attendance audit must preserve the original absence timestamp, not a later teacher reply timestamp. \[Ed0c4a4a07906d9f80ad2102f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ed0c4a4a07906d9f80ad2102f: f9a1904c-9faa-51d3-a54c-06fedde8e761 revision 1 chunk parent:8fb8af548a8ab99c5ffa563a05b57b07c474a901eabe7353a84d5e4573451223 \[7554, 7673\); valid 2026-01-01 through 2026-12-31; SHA-256 12a08f31b050482e629dd97c8164fcde317baa8af9f7d3566cc3890d0b1621cd; quote: The final 2026 attendance audit must retain the original absence timestamp rather than a later teacher reply timestamp.


## gen-tuning-06 / actual

How much advance notice is needed for an ordinary missed-class credit in 2027?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


## gen-tuning-06 / standard

How much advance notice is needed for an ordinary missed-class credit in 2027?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


## gen-tuning-07 / actual

When does a replacement-class credit from a 2027 absence expire?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class. \[Edc3dfaa470b742dc241cc893\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Edc3dfaa470b742dc241cc893: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:5295fab7234e9ba95f2a9da2ee747de808c4ec2257d60533d333e4d95f09acef \[1644, 1747\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class. \[Edc3dfaa470b742dc241cc893\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Edc3dfaa470b742dc241cc893: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:5295fab7234e9ba95f2a9da2ee747de808c4ec2257d60533d333e4d95f09acef \[1644, 1747\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class.


## gen-tuning-07 / standard

When does a replacement-class credit from a 2027 absence expire?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class. \[Edc3dfaa470b742dc241cc893\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Edc3dfaa470b742dc241cc893: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:5295fab7234e9ba95f2a9da2ee747de808c4ec2257d60533d333e4d95f09acef \[1644, 1747\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class. \[Edc3dfaa470b742dc241cc893\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Edc3dfaa470b742dc241cc893: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:5295fab7234e9ba95f2a9da2ee747de808c4ec2257d60533d333e4d95f09acef \[1644, 1747\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A makeup credit issued under the 2027 attendance rules expires 45 calendar days after the missed class.


## gen-tuning-08 / actual

How quickly must a family supply a medical certificate for a 2027 absence exception?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For the 2027 medical exception, a doctor’s certificate must be submitted within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For the 2027 medical exception, the family must submit the doctor’s certificate within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


## gen-tuning-08 / standard

How quickly must a family supply a medical certificate for a 2027 absence exception?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For a 2027 medical absence exception, a family must submit the doctor’s certificate within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For the 2027 medical exception, a family must submit a doctor’s certificate within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


## gen-tuning-09 / actual

How should used and unused absence credits be separated at year end?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

At year end, the final 2027 attendance reconciliation must list unused credits separately from credits already redeemed. \[E93a5da8f2ab2cbecc67b5a00\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E93a5da8f2ab2cbecc67b5a00: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:91dd0288fc7e55634c8ca1e8405b6d1b83c45ae68a76f4915578c8e8b6dd2e62 \[7545, 7652\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The final 2027 attendance reconciliation must list unused credits separately from credits already redeemed.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In the final 2027 attendance reconciliation, list unused absence credits separately from credits already redeemed. \[E93a5da8f2ab2cbecc67b5a00\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E93a5da8f2ab2cbecc67b5a00: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:91dd0288fc7e55634c8ca1e8405b6d1b83c45ae68a76f4915578c8e8b6dd2e62 \[7545, 7652\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The final 2027 attendance reconciliation must list unused credits separately from credits already redeemed.


## gen-tuning-09 / standard

How should used and unused absence credits be separated at year end?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

At the final 2027 attendance reconciliation, list unused credits separately from credits already redeemed. \[E93a5da8f2ab2cbecc67b5a00\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E93a5da8f2ab2cbecc67b5a00: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:91dd0288fc7e55634c8ca1e8405b6d1b83c45ae68a76f4915578c8e8b6dd2e62 \[7545, 7652\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The final 2027 attendance reconciliation must list unused credits separately from credits already redeemed.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

At the final 2027 attendance reconciliation, list unused credits separately from credits already redeemed. \[E93a5da8f2ab2cbecc67b5a00\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E93a5da8f2ab2cbecc67b5a00: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:91dd0288fc7e55634c8ca1e8405b6d1b83c45ae68a76f4915578c8e8b6dd2e62 \[7545, 7652\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The final 2027 attendance reconciliation must list unused credits separately from credits already redeemed.


## gen-tuning-10 / actual

Who must review conflicting active fee schedules before a charge is approved?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The accounts lead must review fee discrepancies between active schedules before any charge is approved. \[Eae5c57f18a8f79b96a45f2ad\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eae5c57f18a8f79b96a45f2ad: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:df4a719a4d98c59038233659858ca77d4e91389554cc28802676e7d377ecabfd \[4292, 4403\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Fee discrepancies between active schedules must be referred to the accounts lead before any charge is approved.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Fee discrepancies between active schedules must be referred to the accounts lead before any charge is approved. \[Eae5c57f18a8f79b96a45f2ad\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eae5c57f18a8f79b96a45f2ad: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:df4a719a4d98c59038233659858ca77d4e91389554cc28802676e7d377ecabfd \[4292, 4403\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Fee discrepancies between active schedules must be referred to the accounts lead before any charge is approved.


## gen-tuning-10 / standard

Who must review conflicting active fee schedules before a charge is approved?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The accounts lead must review fee discrepancies between active schedules before any charge is approved. \[Eae5c57f18a8f79b96a45f2ad\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eae5c57f18a8f79b96a45f2ad: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:df4a719a4d98c59038233659858ca77d4e91389554cc28802676e7d377ecabfd \[4292, 4403\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Fee discrepancies between active schedules must be referred to the accounts lead before any charge is approved.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The accounts lead must review fee discrepancies between active schedules before any charge is approved. \[Eae5c57f18a8f79b96a45f2ad\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eae5c57f18a8f79b96a45f2ad: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:df4a719a4d98c59038233659858ca77d4e91389554cc28802676e7d377ecabfd \[4292, 4403\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Fee discrepancies between active schedules must be referred to the accounts lead before any charge is approved.


## gen-tuning-11 / actual

Which two details are required before the office closes a student account?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Before closing a student account, the enrolment office must record the receipt number and the outstanding balance, even when the balance is zero. \[E6f3a5a9d783c4a5499ee27dd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6f3a5a9d783c4a5499ee27dd: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:41d68b23b6ab367abce6d3f06d5cc9b22f399e98571de1b70b3462137119ea63 \[7513, 7650\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office closes an account only after recording a receipt number and the outstanding balance, even when that balance is zero.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Before the office closes a student account, it must record the receipt number and the outstanding balance, even if the balance is zero. \[E6f3a5a9d783c4a5499ee27dd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6f3a5a9d783c4a5499ee27dd: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:41d68b23b6ab367abce6d3f06d5cc9b22f399e98571de1b70b3462137119ea63 \[7513, 7650\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office closes an account only after recording a receipt number and the outstanding balance, even when that balance is zero.


## gen-tuning-11 / standard

Which two details are required before the office closes a student account?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The office requires a receipt number and the outstanding balance to be recorded before closing a student account. \[E6f3a5a9d783c4a5499ee27dd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6f3a5a9d783c4a5499ee27dd: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:41d68b23b6ab367abce6d3f06d5cc9b22f399e98571de1b70b3462137119ea63 \[7513, 7650\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office closes an account only after recording a receipt number and the outstanding balance, even when that balance is zero.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Before closing a student account, the office must record the receipt number and the outstanding balance, even if the balance is zero. \[E6f3a5a9d783c4a5499ee27dd\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6f3a5a9d783c4a5499ee27dd: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:41d68b23b6ab367abce6d3f06d5cc9b22f399e98571de1b70b3462137119ea63 \[7513, 7650\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office closes an account only after recording a receipt number and the outstanding balance, even when that balance is zero.


## gen-tuning-12 / actual

What annual joining charge appears in the welcome pack payment leaflet?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The welcome pack payment leaflet lists the annual registration charge as AUD 52 per student. \[Ea253fb999313db14240b337d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The welcome pack payment leaflet lists the annual registration charge as AUD 52 per student. \[Ea253fb999313db14240b337d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.


## gen-tuning-12 / standard

What annual joining charge appears in the welcome pack payment leaflet?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The welcome pack payment leaflet lists an annual registration charge of AUD 52 per student. \[Ea253fb999313db14240b337d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The welcome pack payment leaflet lists an annual registration charge of AUD 52 per student. \[Ea253fb999313db14240b337d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.


## gen-tuning-13 / actual

Which date does the welcome leaflet give for the second tuition instalment?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The welcome leaflet gives 25 February 2027 as the due date for the second tuition instalment. \[Ecdb81074b33d6e53e1165f57\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The welcome leaflet gives 25 February 2027 as the due date for the second tuition instalment. \[Ecdb81074b33d6e53e1165f57\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.


## gen-tuning-13 / standard

Which date does the welcome leaflet give for the second tuition instalment?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The welcome leaflet gives 25 February 2027 as the due date for the second tuition instalment. \[Ecdb81074b33d6e53e1165f57\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The welcome leaflet gives 25 February 2027 as the date the second tuition instalment is due. \[Ecdb81074b33d6e53e1165f57\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.


## gen-tuning-14 / actual

What tuition discount does the welcome leaflet promise for the third sibling?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The welcome leaflet promises the third enrolled sibling a 10 percent tuition reduction, excluding registration charges. \[E66d5e8e04f26ac4b9bbe07c4\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The welcome leaflet says the third enrolled sibling receives a 10 percent tuition reduction, excluding registration charges. \[E66d5e8e04f26ac4b9bbe07c4\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.


## gen-tuning-14 / standard

What tuition discount does the welcome leaflet promise for the third sibling?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The welcome leaflet promises the third enrolled sibling a 10 percent tuition reduction, excluding registration charges. \[E66d5e8e04f26ac4b9bbe07c4\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The welcome leaflet promises the third enrolled sibling a 10 percent tuition reduction, excluding registration charges. \[E66d5e8e04f26ac4b9bbe07c4\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.


## gen-tuning-15 / actual

Who receives the electronic receipt under the welcome payment instructions?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Under the welcome payment instructions, electronic receipts are sent to the nominated billing contact, rather than every household contact. \[Ee3b835fac5c9ae5586f1b87e\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ee3b835fac5c9ae5586f1b87e: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:0e41042ef1420b3a93e03f88a422cf26963371cf61cf0d7e144ab09a020d79ed \[7540, 7666\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack requires electronic receipts to be sent to the nominated billing contact rather than every household contact.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Electronic receipts are sent to the nominated billing contact, rather than every household contact. \[Ee3b835fac5c9ae5586f1b87e\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ee3b835fac5c9ae5586f1b87e: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:0e41042ef1420b3a93e03f88a422cf26963371cf61cf0d7e144ab09a020d79ed \[7540, 7666\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack requires electronic receipts to be sent to the nominated billing contact rather than every household contact.


## gen-tuning-15 / standard

Who receives the electronic receipt under the welcome payment instructions?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The electronic receipt is sent to the nominated billing contact, rather than every household contact. \[Ee3b835fac5c9ae5586f1b87e\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ee3b835fac5c9ae5586f1b87e: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:0e41042ef1420b3a93e03f88a422cf26963371cf61cf0d7e144ab09a020d79ed \[7540, 7666\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack requires electronic receipts to be sent to the nominated billing contact rather than every household contact.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Electronic receipts are sent to the nominated billing contact, rather than every household contact. \[Ee3b835fac5c9ae5586f1b87e\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ee3b835fac5c9ae5586f1b87e: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:0e41042ef1420b3a93e03f88a422cf26963371cf61cf0d7e144ab09a020d79ed \[7540, 7666\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack requires electronic receipts to be sent to the nominated billing contact rather than every household contact.


## gen-tuning-16 / actual

When must a Main Campus shuttle seat be reserved?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A Main Campus shuttle seat must be reserved by 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A Main Campus shuttle seat must be reserved by 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.


## gen-tuning-16 / standard

When must a Main Campus shuttle seat be reserved?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A Main Campus shuttle seat must be reserved by 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A Main Campus shuttle seat must be reserved by 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.


## gen-tuning-17 / actual

Where must staff avoid displaying a shuttle collection password?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Staff must never display the Main Campus shuttle handover password on the public passenger sheet. \[E5a5ada2be27562b40cc2bdd1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5a5ada2be27562b40cc2bdd1: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:91653c55c506987f74e9d9b204286ccde2187c6247254d03ba3831dce566a9b9 \[1647, 1775\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: The Main Campus shuttle handover password is collected privately at booking and must never appear on the public passenger sheet.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Staff must never display the Main Campus shuttle handover password on the public passenger sheet. \[E5a5ada2be27562b40cc2bdd1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5a5ada2be27562b40cc2bdd1: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:91653c55c506987f74e9d9b204286ccde2187c6247254d03ba3831dce566a9b9 \[1727, 1774\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: must never appear on the public passenger sheet


## gen-tuning-17 / standard

Where must staff avoid displaying a shuttle collection password?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Staff must never display the Main Campus shuttle handover password on the public passenger sheet. \[E5a5ada2be27562b40cc2bdd1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5a5ada2be27562b40cc2bdd1: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:91653c55c506987f74e9d9b204286ccde2187c6247254d03ba3831dce566a9b9 \[1647, 1775\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: The Main Campus shuttle handover password is collected privately at booking and must never appear on the public passenger sheet.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Staff must never display the Main Campus shuttle handover password on the public passenger sheet. \[E5a5ada2be27562b40cc2bdd1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E5a5ada2be27562b40cc2bdd1: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:91653c55c506987f74e9d9b204286ccde2187c6247254d03ba3831dce566a9b9 \[1727, 1774\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: must never appear on the public passenger sheet


## gen-tuning-18 / actual

What credit is issued for a timely cancellation of the Main Campus bus?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit. \[E35f378349986020510b1eb72\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E35f378349986020510b1eb72: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:50725bc6d34cb1f17521a51bf20c1f0ea5dab9510af9aa0fb64e55f2c26be051 \[3024, 3149\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit. \[E35f378349986020510b1eb72\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E35f378349986020510b1eb72: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:50725bc6d34cb1f17521a51bf20c1f0ea5dab9510af9aa0fb64e55f2c26be051 \[3024, 3149\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit.


## gen-tuning-18 / standard

What credit is issued for a timely cancellation of the Main Campus bus?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit. \[E35f378349986020510b1eb72\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The amount of the transport credit is not specified."\]

- E35f378349986020510b1eb72: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:50725bc6d34cb1f17521a51bf20c1f0ea5dab9510af9aa0fb64e55f2c26be051 \[3024, 3149\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit. \[E35f378349986020510b1eb72\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E35f378349986020510b1eb72: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:50725bc6d34cb1f17521a51bf20c1f0ea5dab9510af9aa0fb64e55f2c26be051 \[3024, 3149\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A Main Campus shuttle reservation cancelled before 10:00 on the travel day receives a transport credit, not a tuition credit.


## gen-tuning-19 / actual

Does an essential companion accompanying a wheelchair user need a paid Main Campus seat?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

An essential companion accompanying a wheelchair user on the Main Campus shuttle does not need a paid second seat. \[E06b5997bcabca87c58267bf3\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E06b5997bcabca87c58267bf3: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

No. A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat. \[E06b5997bcabca87c58267bf3\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E06b5997bcabca87c58267bf3: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.


## gen-tuning-19 / standard

Does an essential companion accompanying a wheelchair user need a paid Main Campus seat?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat. \[E06b5997bcabca87c58267bf3\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E06b5997bcabca87c58267bf3: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat. \[E06b5997bcabca87c58267bf3\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E06b5997bcabca87c58267bf3: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.


## gen-tuning-20 / actual

For Main Campus shuttle MC-12, what collection location and departure time does the reference table list?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

For MC-12, the reference table lists Oak community hall as the location. \[Ea9cfe037285a7f16bd056c02\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \["The table does not establish whether 15:45 is the departure time; its column is labeled “Operational note.”"\]

- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

For MC-12, the table lists “Oak community hall” under “Location or segment” and “15:45” under “Operational note”; it does not identify these entries as a collection location or departure time. \[Ea9cfe037285a7f16bd056c02\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether Oak community hall is the collection location and whether 15:45 is the departure time."\]

- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5778, 5820\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| Location or segment \| Operational note \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

For MC-12, the reference table lists “Oak community hall” under “Location or segment” and “15:45” under “Operational note.” \[Ea9cfe037285a7f16bd056c02\]

The table does not identify Oak community hall as a collection location or 15:45 as a departure time. \[Ea9cfe037285a7f16bd056c02\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether Oak community hall is the collection location and whether 15:45 is the departure time."\]

- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5763, 5820\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| Service code \| Location or segment \| Operational note \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5778, 5820\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| Location or segment \| Operational note \|


## gen-tuning-20 / standard

For Main Campus shuttle MC-12, what collection location and departure time does the reference table list?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

For MC-12, the reference table lists Oak community hall as the location. \[Ea9cfe037285a7f16bd056c02\]

For MC-12, the reference table lists 15:45 in the operational note column. \[Ea9cfe037285a7f16bd056c02\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

For MC-12, the table lists Oak community hall under “Location or segment.” \[Ea9cfe037285a7f16bd056c02\]

The table lists 15:45 as the operational note for MC-12; it does not identify that time as a departure time. \[Ea9cfe037285a7f16bd056c02\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether 15:45 is a departure time."\]

- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5763, 5820\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| Service code \| Location or segment \| Operational note \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5763, 5820\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| Service code \| Location or segment \| Operational note \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

For MC-12, the reference table lists “Oak community hall” under “Location or segment” and “15:45” under “Operational note.” \[Ea9cfe037285a7f16bd056c02\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether Oak community hall is the collection location and 15:45 is the departure time."\]

- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5763, 5820\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| Service code \| Location or segment \| Operational note \|
- Ea9cfe037285a7f16bd056c02: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:2563ab795aeab41ab5b59ea3cb1615d6d6ab00bd9cf51ea3c36082b836db97d9 \[5875, 5913\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: \| MC-12 \| Oak community hall \| 15:45 \|


## gen-tuning-21 / actual

What is the booking deadline for the Riverside Annex shuttle?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


## gen-tuning-21 / standard

What is the booking deadline for the Riverside Annex shuttle?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


## gen-tuning-22 / actual

Where is the pickup point for shuttle route RA-17?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The pickup point for shuttle route RA-17 is the library side gate, not the swimming-pool entrance. \[Ecf3e1e99fe265932ba697521\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecf3e1e99fe265932ba697521: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:c0de8812cb6f481a30f19af396621da3b6e4de377b0b388f45e08e1a9f05c578 \[1656, 1758\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Route RA-17 collects Riverside Annex dancers at the library side gate, not the swimming-pool entrance.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Shuttle route RA-17 collects Riverside Annex dancers at the library side gate, not the swimming-pool entrance. \[Ecf3e1e99fe265932ba697521\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecf3e1e99fe265932ba697521: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:c0de8812cb6f481a30f19af396621da3b6e4de377b0b388f45e08e1a9f05c578 \[1656, 1758\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Route RA-17 collects Riverside Annex dancers at the library side gate, not the swimming-pool entrance.


## gen-tuning-22 / standard

Where is the pickup point for shuttle route RA-17?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The pickup point for shuttle route RA-17 is the library side gate, not the swimming-pool entrance. \[Ecf3e1e99fe265932ba697521\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecf3e1e99fe265932ba697521: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:c0de8812cb6f481a30f19af396621da3b6e4de377b0b388f45e08e1a9f05c578 \[1656, 1758\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Route RA-17 collects Riverside Annex dancers at the library side gate, not the swimming-pool entrance.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

Shuttle route RA-17 picks up Riverside Annex dancers at the library side gate, not the swimming-pool entrance. \[Ecf3e1e99fe265932ba697521\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ecf3e1e99fe265932ba697521: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:c0de8812cb6f481a30f19af396621da3b6e4de377b0b388f45e08e1a9f05c578 \[1656, 1758\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Route RA-17 collects Riverside Annex dancers at the library side gate, not the swimming-pool entrance.


## gen-tuning-23 / actual

By when must an Annex bus reservation be cancelled to receive a transport credit?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

Una reserva del servicio de transporte de Riverside Annex debe cancelarse antes de las 09:00 del día hábil anterior para recibir un crédito de transporte. \[E0c17c841428e83733926f0fa\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E0c17c841428e83733926f0fa: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:d340d5a46998b13da5498cb01221e5a5f72efb0abc9ea5c34a0c70581d9eae28 \[3005, 3124\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: A Riverside Annex shuttle reservation cancelled before 09:00 on the preceding business day receives a transport credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A Riverside Annex shuttle reservation must be cancelled before 09:00 on the preceding business day to receive a transport credit. \[E0c17c841428e83733926f0fa\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E0c17c841428e83733926f0fa: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:d340d5a46998b13da5498cb01221e5a5f72efb0abc9ea5c34a0c70581d9eae28 \[3005, 3124\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: A Riverside Annex shuttle reservation cancelled before 09:00 on the preceding business day receives a transport credit.


## gen-tuning-23 / standard

By when must an Annex bus reservation be cancelled to receive a transport credit?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

To receive a transport credit, a Riverside Annex shuttle reservation must be cancelled before 09:00 on the preceding business day. \[E0c17c841428e83733926f0fa\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E0c17c841428e83733926f0fa: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:d340d5a46998b13da5498cb01221e5a5f72efb0abc9ea5c34a0c70581d9eae28 \[3005, 3124\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: A Riverside Annex shuttle reservation cancelled before 09:00 on the preceding business day receives a transport credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A Riverside Annex shuttle reservation must be cancelled before 09:00 on the preceding business day to receive a transport credit. \[E0c17c841428e83733926f0fa\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E0c17c841428e83733926f0fa: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:d340d5a46998b13da5498cb01221e5a5f72efb0abc9ea5c34a0c70581d9eae28 \[3005, 3124\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: A Riverside Annex shuttle reservation cancelled before 09:00 on the preceding business day receives a transport credit.


## gen-tuning-24 / actual

What must the Annex escort do after the final stop and before leaving the vehicle?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle. \[E1ef3dc237782eb6688132ae1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1ef3dc237782eb6688132ae1: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:492712792778d9e6a51e20a2ec2dea6df67bad4d82cd8a5473d443bbc278f72a \[7686, 7789\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

After the final Riverside Annex shuttle stop and before leaving the vehicle, the escort must call dispatch. \[E1ef3dc237782eb6688132ae1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1ef3dc237782eb6688132ae1: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:492712792778d9e6a51e20a2ec2dea6df67bad4d82cd8a5473d443bbc278f72a \[7686, 7789\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle.


## gen-tuning-24 / standard

What must the Annex escort do after the final stop and before leaving the vehicle?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle. \[E1ef3dc237782eb6688132ae1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1ef3dc237782eb6688132ae1: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:492712792778d9e6a51e20a2ec2dea6df67bad4d82cd8a5473d443bbc278f72a \[7686, 7789\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle. \[E1ef3dc237782eb6688132ae1\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E1ef3dc237782eb6688132ae1: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:492712792778d9e6a51e20a2ec2dea6df67bad4d82cd8a5473d443bbc278f72a \[7686, 7789\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: After the final Riverside Annex shuttle stop, the escort must call dispatch before leaving the vehicle.


## gen-tuning-25 / actual

After meeting the current ordinary-absence notice rule, may a family use the credit in a class with no vacant places?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

In 2027, reporting an ordinary absence at least 24 hours before class earns a makeup credit. \[Ed964d3e67fb1ec2db2a40709\]

The policy distinguishes a promised replacement lesson from a booked place, but does not say whether a family may use a credit in a class with no vacant places. \[Ed964d3e67fb1ec2db2a40709\] \[E1ba0af385653e01067037485\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether a family may use an earned makeup credit in a class with no vacant places."\]

- Ed964d3e67fb1ec2db2a40709: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- Ed964d3e67fb1ec2db2a40709: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[423, 486\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A promised replacement lesson is different from a booked place.
- E1ba0af385653e01067037485: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:25808d19f25adef63d5db64abfc45434292cbc17561281bd32cee4bc09086baa \[4412, 4475\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A promised replacement lesson is different from a booked place.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

Under the 2027 ordinary-notice rule, an absence must be reported at least 24 hours before class to earn a makeup credit. \[Ed964d3e67fb1ec2db2a40709\]

The supplied rules do not establish whether a family may use that credit in a class with no vacant places; they distinguish a promised replacement lesson from a booked place and state that an acknowledgement does not prove a place is available. \[Ed964d3e67fb1ec2db2a40709\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The governing rule on using a makeup credit in a class with no vacant places."\]

- Ed964d3e67fb1ec2db2a40709: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- Ed964d3e67fb1ec2db2a40709: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[423, 486\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A promised replacement lesson is different from a booked place.
- Ed964d3e67fb1ec2db2a40709: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[565, 633\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A friendly acknowledgement does not prove that a place is available.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

I can confirm only the following from the supplied documents:

In 2027, an ordinary absence reported at least 24 hours before class earns a makeup credit. \[Ed964d3e67fb1ec2db2a40709\]

The provided session-capacity text distinguishes a promised replacement lesson from a booked place and says an acknowledgement does not prove a place is available; it does not establish whether a credit may be used in a class with no vacant places. \[E1ba0af385653e01067037485\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The governing session-capacity rule on whether a credit may be used when no places are vacant."\]

- Ed964d3e67fb1ec2db2a40709: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- E1ba0af385653e01067037485: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:25808d19f25adef63d5db64abfc45434292cbc17561281bd32cee4bc09086baa \[4412, 4475\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A promised replacement lesson is different from a booked place.
- E1ba0af385653e01067037485: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:25808d19f25adef63d5db64abfc45434292cbc17561281bd32cee4bc09086baa \[4554, 4622\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: A friendly acknowledgement does not prove that a place is available.


## gen-tuning-25 / standard

After meeting the current ordinary-absence notice rule, may a family use the credit in a class with no vacant places?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

No. The family may not use the credit in a class with no vacant places; an attendance makeup may use only a class whose roster has at least one confirmed vacant place. \[E674c9ce2d321e2fe21fab7ad\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: invalid\_citations
Metadata missing_information (not part of answer): \[\]

- E674c9ce2d321e2fe21fab7ad: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:25808d19f25adef63d5db64abfc45434292cbc17561281bd32cee4bc09086baa \[4315, 4410\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: An attendance makeup may use only a class whose roster has at least one confirmed vacant place.


### Refined V2 — targeted recheck only

Prompt SHA-256: afe44438e7b70e61075a8929c884fda27e3fe91018ace97f8378a2f4370ea6c5

Meeting the ordinary-absence notice rule earns a makeup credit, but the credit may be used only in a class whose roster has at least one confirmed vacant place; therefore, it may not be used in a class with no vacant places. \[Eaedbb81170ae34caffc26d71\] \[E674c9ce2d321e2fe21fab7ad\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- E674c9ce2d321e2fe21fab7ad: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:25808d19f25adef63d5db64abfc45434292cbc17561281bd32cee4bc09086baa \[4315, 4410\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: An attendance makeup may use only a class whose roster has at least one confirmed vacant place.


## gen-tuning-26 / actual

Compare the two active third-sibling discount percentages and identify which fee category they exclude.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Enrolment Office Fee Schedule states that the third enrolled sibling receives a 15 percent tuition reduction, excluding registration charges. \[Ec68e205950c8e185e6289331\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The Welcome Pack Payment Leaflet does not provide a third-sibling discount percentage in the supplied evidence, so the two percentages cannot be compared."\]

- Ec68e205950c8e185e6289331: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:2c3d140e2532afb976f9ff1b8d4396ea10db3774bd8d0d0638779ec13059e2e5 \[2956, 3073\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office gives the third enrolled sibling a 15 percent tuition reduction, excluding registration charges.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Enrolment Office Fee Schedule states a 15% tuition reduction for the third enrolled sibling, excluding registration charges. \[Ec68e205950c8e185e6289331\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The Welcome Pack Payment Leaflet's third-sibling discount percentage and excluded fee category."\]

- Ec68e205950c8e185e6289331: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:2c3d140e2532afb976f9ff1b8d4396ea10db3774bd8d0d0638779ec13059e2e5 \[2956, 3073\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office gives the third enrolled sibling a 15 percent tuition reduction, excluding registration charges.


## gen-tuning-26 / standard

Compare the two active third-sibling discount percentages and identify which fee category they exclude.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The two active schedules state different third-enrolled-sibling tuition reductions: the Enrolment Office Fee Schedule says 15 percent, while the Welcome Pack Payment Leaflet says 10 percent. \[Ede6047e1da06a00567a46013\] \[E66d5e8e04f26ac4b9bbe07c4\]

Both percentages exclude registration charges. \[Ede6047e1da06a00567a46013\] \[E66d5e8e04f26ac4b9bbe07c4\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ede6047e1da06a00567a46013: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:2c3d140e2532afb976f9ff1b8d4396ea10db3774bd8d0d0638779ec13059e2e5 \[2956, 3073\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office gives the third enrolled sibling a 15 percent tuition reduction, excluding registration charges.
- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.
- Ede6047e1da06a00567a46013: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:2c3d140e2532afb976f9ff1b8d4396ea10db3774bd8d0d0638779ec13059e2e5 \[2956, 3073\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office gives the third enrolled sibling a 15 percent tuition reduction, excluding registration charges.
- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The Enrolment Office Fee Schedule lists a 15% tuition reduction for the third enrolled sibling, excluding registration charges. \[Ede6047e1da06a00567a46013\]

The Welcome Pack Payment Leaflet lists a 10% tuition reduction for the third enrolled sibling, also excluding registration charges. \[E66d5e8e04f26ac4b9bbe07c4\]

The two listed percentages differ by 5 percentage points, and the excluded fee category is registration charges. \[Ede6047e1da06a00567a46013\] \[E66d5e8e04f26ac4b9bbe07c4\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Ede6047e1da06a00567a46013: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:2c3d140e2532afb976f9ff1b8d4396ea10db3774bd8d0d0638779ec13059e2e5 \[2956, 3073\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office gives the third enrolled sibling a 15 percent tuition reduction, excluding registration charges.
- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2943, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack gives the third enrolled sibling a 10 percent tuition reduction, excluding registration charges.
- Ede6047e1da06a00567a46013: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:2c3d140e2532afb976f9ff1b8d4396ea10db3774bd8d0d0638779ec13059e2e5 \[3010, 3073\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: a 15 percent tuition reduction, excluding registration charges.
- E66d5e8e04f26ac4b9bbe07c4: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c315b2b75cd64cba3378607bdeb1355b7c00beecc4797817838f131a83a5d1a0 \[2993, 3056\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: a 10 percent tuition reduction, excluding registration charges.


## gen-tuning-27 / actual

For a wheelchair user connecting from Riverside Annex to Main Campus, is a second paid seat needed for the essential companion and who confirms both lists?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

On the Main Campus shuttle, a wheelchair user may bring one essential companion without purchasing a second seat. \[Eb44e800cc5ed93313cdb2c40\]

The protocol says a responsible adult must confirm the correct campus, travel date, and collection arrangement. \[Eb44e800cc5ed93313cdb2c40\] \[E4ce11c3165b4c2acc8ca3464\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether the no-second-seat rule applies to the Riverside Annex leg of this connection.", "Whether the responsible adult confirms both the Riverside Annex and Main Campus lists, or who specifically confirms both lists."\]

- Eb44e800cc5ed93313cdb2c40: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.
- Eb44e800cc5ed93313cdb2c40: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4651, 4744\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A responsible adult must confirm the correct campus, travel date, and collection arrangement.
- E4ce11c3165b4c2acc8ca3464: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:20211c87be8274d2b17caee3f89c9d0527b3fd92e3767f7064da85b0595e0380 \[4653, 4746\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: A responsible adult must confirm the correct campus, travel date, and collection arrangement.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

On the Main Campus shuttle, a wheelchair user may bring one essential companion without purchasing a second seat; the evidence does not establish whether that rule applies to the Riverside Annex-to-Main Campus connection as a whole. \[Eb44e800cc5ed93313cdb2c40\]

A responsible adult must confirm the correct campus, travel date, and collection arrangement. \[E4ce11c3165b4c2acc8ca3464\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether the Main Campus companion rule applies to the Riverside Annex-to-Main Campus connection as a whole.", "Who confirms both lists, and what the two lists are."\]

- Eb44e800cc5ed93313cdb2c40: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.
- E4ce11c3165b4c2acc8ca3464: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:20211c87be8274d2b17caee3f89c9d0527b3fd92e3767f7064da85b0595e0380 \[4653, 4746\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: A responsible adult must confirm the correct campus, travel date, and collection arrangement.


## gen-tuning-27 / standard

For a wheelchair user connecting from Riverside Annex to Main Campus, is a second paid seat needed for the essential companion and who confirms both lists?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

On the Main Campus shuttle, a wheelchair user may bring one essential companion without purchasing a second seat. \[E06b5997bcabca87c58267bf3\]

For travel connecting Riverside Annex to Main Campus, the Annex dispatcher must confirm the essential companion on both passenger lists. \[E952f2bbdbbae1641f574c080\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["Whether the no-second-seat rule also applies to the Riverside Annex shuttle."\]

- E06b5997bcabca87c58267bf3: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.
- E952f2bbdbbae1641f574c080: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:20211c87be8274d2b17caee3f89c9d0527b3fd92e3767f7064da85b0595e0380 \[4373, 4509\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: For travel connecting Riverside Annex to Main Campus, the Annex dispatcher must confirm the essential companion on both passenger lists.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat. \[E06b5997bcabca87c58267bf3\]

For travel connecting Riverside Annex to Main Campus, the Annex dispatcher must confirm the essential companion on both passenger lists. \[E952f2bbdbbae1641f574c080\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E06b5997bcabca87c58267bf3: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0084eb45277117b2a7440b00463d2834a9a975f64e19c9d721d79e865f61e6b8 \[4395, 4507\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: A wheelchair user may bring one essential companion on the Main Campus shuttle without purchasing a second seat.
- E952f2bbdbbae1641f574c080: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:20211c87be8274d2b17caee3f89c9d0527b3fd92e3767f7064da85b0595e0380 \[4373, 4509\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: For travel connecting Riverside Annex to Main Campus, the Annex dispatcher must confirm the essential companion on both passenger lists.


## gen-tuning-28 / actual

If a teacher sees different temporary-key deposits in the two active access documents, what are the amounts and who must confirm the rule?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Main Campus Building Access Manual lists a refundable temporary key deposit of AUD 20. \[E6687eafd3ba99e09e92658a6\]

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35. \[Ebcdfbd8baf92bc0843f346da\]

The documents instruct staff to establish which location and document the visitor is asking about, and say the administrator checks access logs, room identifiers, and key-return receipts before replying. \[Ec830a2ff96b66eaccded4f2b\] \[E6687eafd3ba99e09e92658a6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which person or role has authority to confirm which deposit rule applies when the two documents list different amounts."\]

- E6687eafd3ba99e09e92658a6: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk parent:285b08ad149c8a3818b208d22ed7135b0312ee16661d83f693830a7debd34a8b \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.
- Ebcdfbd8baf92bc0843f346da: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- Ec830a2ff96b66eaccded4f2b: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk parent:53b8737d477f11301df8999faa519f487fb23dce654ee9adfba3f2fe79b2c7ac \[3616, 3712\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The administrator checks access logs, room identifiers, and key-return receipts before replying.
- E6687eafd3ba99e09e92658a6: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk parent:285b08ad149c8a3818b208d22ed7135b0312ee16661d83f693830a7debd34a8b \[3024, 3123\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: Staff establish which location and document the visitor is asking about before giving instructions.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Main Campus Building Access Manual lists a refundable temporary key deposit of AUD 20. \[E6687eafd3ba99e09e92658a6\]

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35. \[Ebcdfbd8baf92bc0843f346da\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["The role or person responsible for confirming which deposit rule applies."\]

- E6687eafd3ba99e09e92658a6: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk parent:285b08ad149c8a3818b208d22ed7135b0312ee16661d83f693830a7debd34a8b \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.
- Ebcdfbd8baf92bc0843f346da: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.


## gen-tuning-28 / standard

If a teacher sees different temporary-key deposits in the two active access documents, what are the amounts and who must confirm the rule?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

The Main Campus manual lists a refundable temporary key deposit of AUD 20. \[E6e975a9b6a34682b3ade43e9\]

The facilities desk addendum lists a refundable temporary key deposit of AUD 35. \[Ecb39f58b13e6be4ca52e9d0b\]

When active building-access documents disagree, the facilities manager must confirm the rule before a key is issued. \[Ee5caf29c9def6955592b50be\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6e975a9b6a34682b3ade43e9: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk parent:285b08ad149c8a3818b208d22ed7135b0312ee16661d83f693830a7debd34a8b \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.
- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- Ee5caf29c9def6955592b50be: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:9fa4291d1f140ea467fc4ba920e80afecd8e3320888297bb280ba322f89dbd76 \[1602, 1718\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: When active building-access documents disagree, the facilities manager must confirm the rule before a key is issued.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

The Main Campus Building Access Manual lists a refundable temporary key deposit of AUD 20. \[E6e975a9b6a34682b3ade43e9\]

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35. \[Ecb39f58b13e6be4ca52e9d0b\]

When active building-access documents disagree, the facilities manager must confirm the rule before a key is issued. \[Ee5caf29c9def6955592b50be\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- E6e975a9b6a34682b3ade43e9: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk parent:285b08ad149c8a3818b208d22ed7135b0312ee16661d83f693830a7debd34a8b \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.
- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- Ee5caf29c9def6955592b50be: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:9fa4291d1f140ea467fc4ba920e80afecd8e3320888297bb280ba322f89dbd76 \[1602, 1718\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: When active building-access documents disagree, the facilities manager must confirm the rule before a key is issued.


## gen-tuning-29 / actual

The two active documents disagree about annual registration. Tell me what each says and decide which amount is authoritative for charging me.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet sets the annual registration charge at AUD 52 per student. \[Ea253fb999313db14240b337d\]

The Enrolment Office Fee Schedule sets the annual registration charge at AUD 48 per student. \[Eb5902a32dee375e7de433564\]

The supplied documents do not establish which amount is authoritative for charging: the leaflet says it does not authorize staff to resolve a disagreement between fee schedules, and says printed amounts are not permission to silently override another active schedule. \[Ee5c843060f3b76b4928d35b6\] \[Ea253fb999313db14240b337d\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which registration charge the studio authorizes for charging when these two active documents disagree."\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.
- Eb5902a32dee375e7de433564: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:13516f6fda6d7e456efad43e11341936c983ae369c3194db3f10817927eaf091 \[318, 406\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office schedule sets the annual registration charge at AUD 48 per student.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4280, 4419\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack payment leaflet describes tuition collection and does not authorise staff to resolve a disagreement between fee schedules.
- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[402, 519\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: A printed amount is evidence of what that document says, not permission to silently override another active schedule.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet states an annual registration charge of AUD 52 per student. \[Ea253fb999313db14240b337d\]

The Enrolment Office Fee Schedule states an annual registration charge of AUD 48 per student. \[Eb5902a32dee375e7de433564\]

The documents do not establish which amount is authoritative for charging: each says a printed amount does not permit silently overriding another active schedule and that both sources should be preserved when referring a discrepancy. \[Ea253fb999313db14240b337d\] \[Eb5902a32dee375e7de433564\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which amount is authorized for charging."\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.
- Eb5902a32dee375e7de433564: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:13516f6fda6d7e456efad43e11341936c983ae369c3194db3f10817927eaf091 \[318, 406\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office schedule sets the annual registration charge at AUD 48 per student.
- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[402, 577\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: A printed amount is evidence of what that document says, not permission to silently override another active schedule. Staff preserve both sources when referring a discrepancy.
- Eb5902a32dee375e7de433564: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:13516f6fda6d7e456efad43e11341936c983ae369c3194db3f10817927eaf091 \[408, 583\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: A printed amount is evidence of what that document says, not permission to silently override another active schedule. Staff preserve both sources when referring a discrepancy.


## gen-tuning-29 / standard

The two active documents disagree about annual registration. Tell me what each says and decide which amount is authoritative for charging me.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet sets the annual registration charge at AUD 52 per student. \[Ea253fb999313db14240b337d\]

The Enrolment Office Fee Schedule sets the annual registration charge at AUD 48 per student. \[Eb5902a32dee375e7de433564\]

The supplied documents do not establish which amount is authoritative for charging you; the Welcome Pack Payment Leaflet says it does not authorise staff to resolve a disagreement between fee schedules. \[Ee5c843060f3b76b4928d35b6\] \[Ea253fb999313db14240b337d\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which amount, if either, is authoritative for charging under an applicable fee-resolution rule."\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.
- Eb5902a32dee375e7de433564: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:13516f6fda6d7e456efad43e11341936c983ae369c3194db3f10817927eaf091 \[318, 406\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office schedule sets the annual registration charge at AUD 48 per student.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4280, 4419\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack payment leaflet describes tuition collection and does not authorise staff to resolve a disagreement between fee schedules.
- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[402, 577\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: A printed amount is evidence of what that document says, not permission to silently override another active schedule. Staff preserve both sources when referring a discrepancy.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet states an annual registration charge of AUD 52 per student. \[Ea253fb999313db14240b337d\]

The Enrolment Office Fee Schedule states an annual registration charge of AUD 48 per student. \[Eb5902a32dee375e7de433564\]

The supplied documents do not establish which amount is authoritative for charging: each says its printed amount is not permission to silently override another active schedule, and that staff preserve both sources when referring a discrepancy. \[Ea253fb999313db14240b337d\] \[Eb5902a32dee375e7de433564\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["The governing authority decision specifying which schedule controls the registration charge."\]

- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[317, 400\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet sets the annual registration charge at AUD 52 per student.
- Eb5902a32dee375e7de433564: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:13516f6fda6d7e456efad43e11341936c983ae369c3194db3f10817927eaf091 \[318, 406\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: The enrolment office schedule sets the annual registration charge at AUD 48 per student.
- Ea253fb999313db14240b337d: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:b975211a991f956bba93f64bae1e8c24764a0cb21daecea04dec0ae40976bba3 \[402, 577\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: A printed amount is evidence of what that document says, not permission to silently override another active schedule. Staff preserve both sources when referring a discrepancy.
- Eb5902a32dee375e7de433564: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:13516f6fda6d7e456efad43e11341936c983ae369c3194db3f10817927eaf091 \[408, 583\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: A printed amount is evidence of what that document says, not permission to silently override another active schedule. Staff preserve both sources when referring a discrepancy.


## gen-tuning-30 / actual

The active schedules disagree about my second tuition due date. State the dates and tell me which one definitively governs my payment.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet says the second tuition instalment is due on 25 February 2027. \[Ecdb81074b33d6e53e1165f57\]

The Enrolment Office Fee Schedule says the second tuition instalment is due on 18 February 2027. \[E257537103dbb3d6e2e105591\]

The evidence does not establish which date definitively governs, because the welcome pack leaflet says it does not authorise staff to resolve disagreement between fee schedules. \[Ee5c843060f3b76b4928d35b6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which fee schedule definitively governs the second tuition instalment due date."\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.
- E257537103dbb3d6e2e105591: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:c26227997b44c45316daacd3a13f06030f928bd870a136eb52fa13c4d3ef2c01 \[1635, 1729\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Under the enrolment office schedule, the second tuition instalment is due on 18 February 2027.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4280, 4419\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack payment leaflet describes tuition collection and does not authorise staff to resolve a disagreement between fee schedules.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet states that the second tuition instalment is due on 25 February 2027. \[Ecdb81074b33d6e53e1165f57\]

The Enrolment Office Fee Schedule states that the second tuition instalment is due on 18 February 2027. \[E257537103dbb3d6e2e105591\]

The supplied text does not establish which schedule definitively governs: the Welcome Pack Payment Leaflet says it does not authorise staff to resolve a disagreement between fee schedules, and says staff preserve both sources when referring a discrepancy. \[Ee5c843060f3b76b4928d35b6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which schedule is authoritative for the second tuition due date."\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.
- E257537103dbb3d6e2e105591: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:c26227997b44c45316daacd3a13f06030f928bd870a136eb52fa13c4d3ef2c01 \[1635, 1729\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Under the enrolment office schedule, the second tuition instalment is due on 18 February 2027.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4280, 4419\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack payment leaflet describes tuition collection and does not authorise staff to resolve a disagreement between fee schedules.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4539, 4596\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: Staff preserve both sources when referring a discrepancy.


## gen-tuning-30 / standard

The active schedules disagree about my second tuition due date. State the dates and tell me which one definitively governs my payment.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet states that the second tuition instalment is due on 25 February 2027. \[Ecdb81074b33d6e53e1165f57\]

The Enrolment Office Fee Schedule states that the second tuition instalment is due on 18 February 2027. \[E257537103dbb3d6e2e105591\]

The supplied documents do not establish which date definitively governs, because the welcome pack leaflet does not authorise staff to resolve a disagreement between fee schedules. \[Ee5c843060f3b76b4928d35b6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["An authoritative resolution establishing which schedule's due date governs the payment."\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.
- E257537103dbb3d6e2e105591: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:c26227997b44c45316daacd3a13f06030f928bd870a136eb52fa13c4d3ef2c01 \[1635, 1729\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Under the enrolment office schedule, the second tuition instalment is due on 18 February 2027.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4280, 4419\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack payment leaflet describes tuition collection and does not authorise staff to resolve a disagreement between fee schedules.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Welcome Pack Payment Leaflet states that the second tuition instalment is due on 25 February 2027. \[Ecdb81074b33d6e53e1165f57\]

The Enrolment Office Fee Schedule states that the second tuition instalment is due on 18 February 2027. \[E257537103dbb3d6e2e105591\]

The supplied documents do not establish which schedule definitively governs; the welcome pack says it does not authorise staff to resolve a disagreement between fee schedules. \[Ee5c843060f3b76b4928d35b6\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which schedule is authoritative for the payment."\]

- Ecdb81074b33d6e53e1165f57: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:669c2f2a40a4634918c9e44ff8e572bc07f03869dde3b85e0130c32e07d1f01a \[1629, 1716\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack leaflet says the second tuition instalment is due on 25 February 2027.
- E257537103dbb3d6e2e105591: d5bb16f4-207b-54a6-860c-0ea42164556e revision 1 chunk parent:c26227997b44c45316daacd3a13f06030f928bd870a136eb52fa13c4d3ef2c01 \[1635, 1729\); valid 2027-01-01 through 2027-12-31; SHA-256 dd08419811511f20a52643b5673fab06dabd018eee143c7dfdeb3603e04df4fd; quote: Under the enrolment office schedule, the second tuition instalment is due on 18 February 2027.
- Ee5c843060f3b76b4928d35b6: 74ca718b-f99d-55d9-83f7-64a7c5aaeb01 revision 1 chunk parent:c646ee6d883bc73c2dff330c8f7e19b5bc6d647a0778431522bf0f00e64680b2 \[4280, 4419\); valid 2027-01-01 through 2027-12-31; SHA-256 4bfe0c526728625a4453d6665cfa44ecda4d4def6ec83bfc868c3a78955ed752; quote: The welcome pack payment leaflet describes tuition collection and does not authorise staff to resolve a disagreement between fee schedules.


## gen-tuning-31 / actual

The two active access documents list different key deposits. State both amounts and decide which deposit I must pay without asking anyone else.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35. \[Ecb39f58b13e6be4ca52e9d0b\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The other amount the question refers to and which deposit, if any, you must pay are not established by the supplied evidence."\]

- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35. \[Ecb39f58b13e6be4ca52e9d0b\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: insufficient\_evidence
Metadata missing_information (not part of answer): \["The key-deposit amount listed in the Main Campus Building Access Manual.", "Which deposit is required when the documents differ, including which source controls."\]

- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.


## gen-tuning-31 / standard

The two active access documents list different key deposits. State both amounts and decide which deposit I must pay without asking anyone else.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I can confirm only the following from the supplied documents:

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35, while the Main Campus manual lists AUD 20. \[Ecb39f58b13e6be4ca52e9d0b\] \[E4b129401ce1edd36037b17a0\]

The supplied documents list different amounts, so the evidence does not establish which deposit you must pay. \[Ecb39f58b13e6be4ca52e9d0b\] \[E4b129401ce1edd36037b17a0\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which document governs your access arrangement and which deposit applies to you."\]

- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- E4b129401ce1edd36037b17a0: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk oracle:f1 \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.
- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- E4b129401ce1edd36037b17a0: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk oracle:f1 \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I can confirm only the following from the supplied documents:

The Facilities Desk Access Addendum lists a refundable temporary key deposit of AUD 35. \[Ecb39f58b13e6be4ca52e9d0b\]

The Main Campus Building Access Manual lists a refundable temporary key deposit of AUD 20. \[E4b129401ce1edd36037b17a0\]

The evidence does not establish which amount governs, so I cannot determine which deposit you must pay. \[Ecb39f58b13e6be4ca52e9d0b\] \[E4b129401ce1edd36037b17a0\]

The remaining details cannot be confirmed from this evidence.

Metadata reason: conflicting\_sources
Metadata missing_information (not part of answer): \["Which document is authoritative for the deposit amount."\]

- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- E4b129401ce1edd36037b17a0: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk oracle:f1 \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.
- Ecb39f58b13e6be4ca52e9d0b: 80d8b8c7-31ec-5161-b5b2-090e51296c74 revision 1 chunk parent:dd085521e8202247ae8c8ff711bdcf6d69d90314ab2b1699e325514ad1296f77 \[314, 394\); valid 2027-01-01 through 2027-12-31; SHA-256 fd6e135d5281dc42744d003d414429a54de200425c06b6ecf20f88121dd628e6; quote: The facilities desk addendum lists a refundable temporary key deposit of AUD 35.
- E4b129401ce1edd36037b17a0: f745cb9c-7168-515b-ab07-c5de3faaec20 revision 1 chunk oracle:f1 \[2865, 2939\); valid 2027-01-01 through 2027-12-31; SHA-256 6f65a90f7c4c63a0a7136a7e85dd85571320f90c3b37b26065a18f1aafc29e7e; quote: The Main Campus manual lists a refundable temporary key deposit of AUD 20.


## gen-tuning-32 / actual

What is the price of a single adult drop-in salsa lesson in 2027?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The price of a single adult drop-in salsa lesson in 2027 is not stated in the supplied evidence."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The price of a single adult drop-in salsa lesson in 2027."\]



## gen-tuning-32 / standard

What is the price of a single adult drop-in salsa lesson in 2027?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The price of a single adult drop-in salsa lesson in 2027 is not stated in the supplied evidence."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The 2027 price of a single adult drop-in salsa lesson."\]



## gen-tuning-33 / actual

Which insurer covers the Riverside Annex shuttle and what is its policy number?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The insurer covering the Riverside Annex shuttle and its policy number are not stated in the supplied evidence."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["Insurer and policy number"\]



## gen-tuning-33 / standard

Which insurer covers the Riverside Annex shuttle and what is its policy number?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The insurer covering the Riverside Annex shuttle and its policy number are not stated in the supplied evidence."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-tuning-34 / actual

What interest rate applies to overdue tuition instalments?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The applicable interest rate for overdue tuition instalments."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The interest rate for overdue tuition instalments."\]



## gen-tuning-34 / standard

What interest rate applies to overdue tuition instalments?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \["The interest rate, if any, that applies to overdue tuition instalments."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-tuning-35 / actual

What deadline applies to an ordinary absence?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-tuning-35 / standard

What deadline applies to an ordinary absence?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-tuning-36 / actual

What deadline applies to an ordinary absence?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-tuning-36 / standard

What deadline applies to an ordinary absence?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: no\_applicable\_evidence
Metadata missing_information (not part of answer): \[\]



## gen-tuning-37 / actual

Which shuttle reservation deadline applies to my journey? I have not said whether I travel from Main Campus or Riverside Annex.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I need more details before I can confirm an answer.

For Main Campus, shuttle seats must be reserved by 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

For Riverside Annex, shuttle seats must be reserved by 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Which campus your journey is from."\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.
- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I need more details before I can confirm an answer.

If your journey is from Main Campus, the reservation deadline is 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

If your journey is from Riverside Annex, the reservation deadline is 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Which campus your journey is from: Main Campus or Riverside Annex."\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.
- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


## gen-tuning-37 / standard

Which shuttle reservation deadline applies to my journey? I have not said whether I travel from Main Campus or Riverside Annex.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I need more details before I can confirm an answer.

For travel from Main Campus, shuttle seats must be reserved by 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

For travel from Riverside Annex, shuttle seats must be reserved by 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Which campus you are travelling from."\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.
- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I need more details before I can confirm an answer.

If your journey is from Main Campus, the shuttle reservation deadline is 16:00 on the preceding business day. \[Ef4ba5fd533df0cccc5bb605f\]

If your journey is from Riverside Annex, the shuttle reservation deadline is 12:00 two business days before travel. \[E6088199fdf9a2bbb4ee6741d\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether your journey is from Main Campus or Riverside Annex."\]

- Ef4ba5fd533df0cccc5bb605f: 97efc8d4-f336-5bd2-a17c-fd085ff59c6d revision 1 chunk parent:0fd21a305c46ddaf63ed160f203bc12b0ce16942a7aaebc5c89088470c334f7d \[317, 399\); valid 2027-01-01 through 2027-12-31; SHA-256 f62858fed472df8a12e102d4795a4c8a4fbaa4363d417eb2afabd8b41e8ba729; quote: Main Campus shuttle seats must be reserved by 16:00 on the preceding business day.
- E6088199fdf9a2bbb4ee6741d: fd7e8629-4d83-558b-836a-b30da0be3a08 revision 1 chunk parent:a931f4dbeb1e954bebec57ffd6ee51e797d5534d77e6c14fa826aaaf9a3832d7 \[321, 409\); valid 2027-01-01 through 2027-12-31; SHA-256 db328c416d5c18a285293a2e84c5abf65e58dbb920653b8907a2c36f0d8392af; quote: Riverside Annex shuttle seats must be reserved by 12:00 two business days before travel.


## gen-tuning-38 / actual

Which absence notice or medical-document deadline applies to me? I have not said whether this is an ordinary absence or a medical exception.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I need more details before I can confirm an answer.

For an ordinary absence in 2027, notice must be given at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

For the 2027 medical exception, a doctor’s certificate must be submitted within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether your absence is ordinary or qualifies for the medical exception."\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I need more details before I can confirm an answer.

If this is an ordinary absence, it must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

If this is a medical exception, a doctor’s certificate must be submitted within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether this is an ordinary absence or a medical exception."\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


## gen-tuning-38 / standard

Which absence notice or medical-document deadline applies to me? I have not said whether this is an ordinary absence or a medical exception.

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I need more details before I can confirm an answer.

For an ordinary absence in 2027, report it at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

For the 2027 medical exception, submit a doctor’s certificate within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether this is an ordinary absence or a medical exception."\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I need more details before I can confirm an answer.

If this is an ordinary absence, it must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

If this is a medical exception, a doctor’s certificate must be submitted within three calendar days of the missed class. \[E838ea53e9ddeb80eec1a10e9\]

Metadata reason: missing\_user\_details
Metadata missing_information (not part of answer): \["Whether this is an ordinary absence or a medical exception."\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[329, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.
- E838ea53e9ddeb80eec1a10e9: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:b5de7f7157963893e633ea7570d3bfad32d3aaad1343ce082dbce583e32d0ded \[2970, 3085\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: The 2027 medical exception accepts a doctor’s certificate submitted within three calendar days of the missed class.


## gen-tuning-39 / actual

Is there a vacant Main Campus shuttle seat for my child today, and has my reservation already been confirmed?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Whether a Main Campus shuttle seat is vacant for your child today.", "Whether your reservation has been confirmed."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Current Main Campus shuttle seat availability and reservation confirmation records"\]



## gen-tuning-39 / standard

Is there a vacant Main Campus shuttle seat for my child today, and has my reservation already been confirmed?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \["Whether a Main Campus shuttle seat is vacant for your child today.", "Whether your reservation has been confirmed."\]



### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

I cannot confirm an answer from the supplied evidence.

Metadata reason: requires\_live\_data
Metadata missing_information (not part of answer): \[\]



## gen-tuning-40 / actual

How much advance notice is needed for an ordinary missed-class credit in 2027?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


## gen-tuning-40 / standard

How much advance notice is needed for an ordinary missed-class credit in 2027?

### V1 baseline

Prompt SHA-256: 0788e2c0e6e14dab32c3832c8ef70196d24ac45dea315412ce3722287073e49e

In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.


### Initial V2

Prompt SHA-256: eb545bcf62b388350eca55d9960f3dcbc752f500280d902d7e56e4a18fdc55d2

For an ordinary missed-class makeup credit in 2027, the absence must be reported at least 24 hours before class. \[Eaedbb81170ae34caffc26d71\]

Metadata reason: supported
Metadata missing_information (not part of answer): \[\]

- Eaedbb81170ae34caffc26d71: bf97b588-ebc1-5bdf-9ec6-7475730639e7 revision 1 chunk parent:a6dc88c43b5f309f1a17df95d0c24f4d776bffd33f1eb25a4ac9799e8a4e4a52 \[320, 421\); valid 2027-01-01 through 2027-12-31; SHA-256 b278275fb6efc84ace9cb880b1973a9b725677bd1920bf2ce546a925740e6712; quote: In 2027, an ordinary absence must be reported at least 24 hours before class to earn a makeup credit.

