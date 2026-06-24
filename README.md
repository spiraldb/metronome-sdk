# metronome-sdk

An unofficial Rust client for the [Metronome](https://metronome.com) billing API,
generated from Metronome's published OpenAPI spec with
[progenitor](https://github.com/oxidecomputer/progenitor).

> Metronome doesn't ship a Rust SDK (only TypeScript and Go). This crate
> generates a typed, async client (`reqwest` + `serde`) from their OpenAPI spec.
> `src/lib.rs` is **generated — do not hand-edit it.** Re-run `./scripts/generate.sh`
> instead.

## Usage

Metronome uses bearer-token auth. progenitor doesn't inject the token itself, so
attach it as a default header on the `reqwest::Client` and hand that to the
generated client:

```rust
use std::str::FromStr;
use metronome_sdk::Client;
use metronome_sdk::types::IngestV1BodyItem;

fn metronome(token: &str) -> Client {
    let mut headers = reqwest::header::HeaderMap::new();
    let mut auth = reqwest::header::HeaderValue::from_str(&format!("Bearer {token}")).unwrap();
    auth.set_sensitive(true);
    headers.insert(reqwest::header::AUTHORIZATION, auth);

    let http = reqwest::Client::builder()
        .default_headers(headers)
        .build()
        .unwrap();

    Client::new_with_client("https://api.metronome.com", http)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = metronome(&std::env::var("METRONOME_API_KEY")?);

    // Ingest a usage event. The id/customer/type fields are validated newtypes,
    // so build them with FromStr (or TryFrom) rather than a bare String.
    let events = vec![IngestV1BodyItem {
        transaction_id: FromStr::from_str("txn-0001")?,
        customer_id: FromStr::from_str("cust_abc123")?,
        event_type: FromStr::from_str("api_request")?,
        timestamp: "2026-06-15T00:00:00Z".to_string(), // RFC 3339
        properties: serde_json::json!({ "tokens": 4096 })
            .as_object().unwrap().clone(),
    }];
    client.ingest_v1(&events).await?;

    Ok(())
}
```

Every Metronome endpoint is available as an `async` method on `Client` (119 in
total) — e.g. `ingest_v1`, `search_events_v1`, `create_billable_metric_v1`.
Request/response types live under `metronome_sdk::types`. Constrained string
fields are generated as validated newtypes; construct them with
`FromStr`/`TryFrom` (both return a `ConversionError` if validation fails).

## Regenerating

```bash
cargo install cargo-progenitor --version 0.14.0   # one-time
./scripts/generate.sh             # regenerate from the vendored spec/
./scripts/generate.sh --refresh   # re-download the spec from Metronome, then regenerate
```

### Why the spec needs patching

Metronome's published OpenAPI spec has constructs that progenitor/typify can't
consume directly (the official Go/TS SDKs use a private Stainless overlay we
don't have). `scripts/patch_spec.py` applies three mechanical, deterministic
fixes before generation:

1. **Case-insensitive enums → `string`** (618 of them). The spec enumerates
   every casing of each value (`count`/`Count`/`COUNT`), which can't map to
   unique Rust variants. Downgrading to `string` round-trips losslessly
   regardless of the casing the API returns.
2. **Mis-typed string enums → `type: string`** (7). Some enums declare
   `type: object` despite having string values (e.g. `billable_status`).
3. **Stray scalar `format` on array/object nodes stripped** (2). e.g. a
   `type: array` carrying `format: uuid`.

If a future spec revision introduces a new unsupported construct, generation
will fail loudly; extend `patch_spec.py` with a new rule.
