# Round 2 v2 setup

Round 2 v2 keeps the participant datasets and answer key encrypted at rest.

## 1. Prepare the encrypted data

Run from the repository root:

```bash
python tools/prepare_round2_data.py \
  --datasets /path/to/cansat_datasets_v2.zip \
  --answers /path/to/ORGANIZER_KEYS_v2.zip
```

If no key is supplied, the script prints a new 32-byte base64url deployment secret. Save it privately and set it as `ROUND2_DATA_KEY`.

The generated `round2_data/` directory contains only encrypted/base64 data files. Commit those generated files to the repository.

## 2. Deployment secrets

Set these environment variables on the server:

- `ROUND2_DATA_KEY`: the 32-byte base64url key generated above
- `ROUND2_STAGE2_PASSWORD`: the organizer password for the Stage 2 ZIP
- `ROUND2_STAGE3_PASSWORD`: the organizer password for the Stage 3 ZIP

Optional:

- `ROUND2_DATA_DIR`: defaults to `round2_data`
- `ROUND2_ANSWER_KEY_PATH`: defaults to `round2_data/answer_key.b64`

Never commit these secret values.

## 3. Release control

The Flight Director admin console has two Round 2 stage controls:

- `round2_stage2_active`
- `round2_stage3_active`

Stage 2 and Stage 3 remain server-side locked until their respective admin toggle is enabled.

## 4. Round 2 behaviour

- Each authenticated team receives only its own `dataset_XX` package.
- Stage 1 exposes `mission_brief.md` and `telemetry.csv`.
- Python runs client-side through Pyodide. Participant code is not submitted to the server.
- Stage 2 exposes `groundstation.log` only after release.
- Stage 3 exposes `config.json` only after release.
- Anomaly reports contain timestamp, subsystem, and description.
- Correct report: +10.
- Wrong report: -5.
- Timestamp tolerance: ±1 second.
- Seven correct anomalies complete Round 2 and unlock Round 3.
- Focus/tab changes are logged for admin review, but are not automatically penalized.

Round 1 code and routes are not modified by the Round 2 v2 implementation.
