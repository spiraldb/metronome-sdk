// Compile-check for the README construction example (no network/runtime needed).
use std::str::FromStr;
use metronome_sdk::Client;
use metronome_sdk::types::IngestV1BodyItem;

#[allow(dead_code)]
fn build() -> Result<(Client, Vec<IngestV1BodyItem>), Box<dyn std::error::Error>> {
    let mut headers = reqwest::header::HeaderMap::new();
    let mut auth = reqwest::header::HeaderValue::from_str("Bearer x")?;
    auth.set_sensitive(true);
    headers.insert(reqwest::header::AUTHORIZATION, auth);
    let http = reqwest::Client::builder().default_headers(headers).build()?;
    let client = Client::new_with_client("https://api.metronome.com", http);

    let events = vec![IngestV1BodyItem {
        transaction_id: FromStr::from_str("txn-0001")?,
        customer_id: FromStr::from_str("cust_abc123")?,
        event_type: FromStr::from_str("api_request")?,
        timestamp: "2026-06-15T00:00:00Z".to_string(),
        properties: serde_json::json!({ "tokens": 4096 }).as_object().unwrap().clone(),
    }];
    Ok((client, events))
}

fn main() {}
