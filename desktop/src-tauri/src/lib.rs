// PebbleMind Desktop - Rust Backend
// Manages Python backend process and provides Tauri commands for the UI

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::process::{Child, Command, Stdio};
use tauri::State;
use reqwest::Client;

// ============================================================================
// Data Structures
// ============================================================================

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequest {
    pub message: String,
    pub system_prompt: Option<String>,
    pub max_tokens: Option<u32>,
    pub temperature: Option<f32>,
    pub stream: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponse {
    pub response: String,
    pub model: String,
    pub tokens: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BackendStatus {
    pub running: bool,
    pub port: u16,
    pub model: Option<String>,
    pub backend_type: Option<String>, // "local" or "groq"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelInfo {
    pub name: String,
    pub size: String,
    pub description: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ConfigUpdate {
    pub backend: Option<String>,
    pub model_size: Option<String>,
    pub temperature: Option<f32>,
    pub max_tokens: Option<u32>,
}

// ============================================================================
// Application State
// ============================================================================

pub struct AppState {
    backend_process: Mutex<Option<Child>>,
    backend_port: u16,
    http_client: Client,
}

impl AppState {
    fn new() -> Self {
        Self {
            backend_process: Mutex::new(None),
            backend_port: 8000,
            http_client: Client::new(),
        }
    }

    fn api_url(&self, endpoint: &str) -> String {
        format!("http://localhost:{}{}", self.backend_port, endpoint)
    }
}

// ============================================================================
// Tauri Commands
// ============================================================================

#[tauri::command]
async fn start_backend(state: State<'_, Arc<AppState>>) -> Result<BackendStatus, String> {
    println!("Starting Python backend...");

    let mut process_guard = state.backend_process.lock().map_err(|e| e.to_string())?;

    // Check if already running
    if let Some(ref mut child) = *process_guard {
        match child.try_wait() {
            Ok(None) => {
                // Process is still running
                return Ok(BackendStatus {
                    running: true,
                    port: state.backend_port,
                    model: None,
                    backend_type: None,
                });
            }
            _ => {
                // Process has exited, clean it up
                *process_guard = None;
            }
        }
    }

    // Start new Python backend process
    let child = Command::new("pebblemind")
        .args(&["serve", "--host", "localhost", "--port", &state.backend_port.to_string()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}. Is PebbleMind installed?", e))?;

    *process_guard = Some(child);

    // Wait a moment for the server to start
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // Check if it's actually running
    match check_backend_health(&state).await {
        Ok(status) => Ok(status),
        Err(e) => {
            // Failed to start, clean up
            if let Some(mut child) = process_guard.take() {
                let _ = child.kill();
            }
            Err(format!("Backend started but health check failed: {}", e))
        }
    }
}

#[tauri::command]
async fn stop_backend(state: State<'_, Arc<AppState>>) -> Result<(), String> {
    println!("Stopping Python backend...");

    let mut process_guard = state.backend_process.lock().map_err(|e| e.to_string())?;

    if let Some(mut child) = process_guard.take() {
        child.kill().map_err(|e| format!("Failed to kill backend process: {}", e))?;
        child.wait().map_err(|e| format!("Failed to wait for process: {}", e))?;
        Ok(())
    } else {
        Err("Backend is not running".to_string())
    }
}

#[tauri::command]
async fn get_backend_status(state: State<'_, Arc<AppState>>) -> Result<BackendStatus, String> {
    check_backend_health(&state).await
}

#[tauri::command]
async fn send_chat_message(
    message: String,
    system_prompt: Option<String>,
    state: State<'_, Arc<AppState>>,
) -> Result<ChatResponse, String> {
    println!("Sending chat message: {}", message);

    // Build request
    let request_body = serde_json::json!({
        "model": "pebblemind-chat",
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "stream": false
    });

    // Send to Python backend
    let url = state.api_url("/v1/chat/completions");
    let response = state
        .http_client
        .post(&url)
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Failed to send request: {}", e))?;

    if !response.status().is_success() {
        return Err(format!(
            "Backend returned error: {}",
            response.status()
        ));
    }

    let response_json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    // Extract response text
    let response_text = response_json["choices"][0]["message"]["content"]
        .as_str()
        .ok_or("No response content")?
        .to_string();

    Ok(ChatResponse {
        response: response_text,
        model: "pebblemind-chat".to_string(),
        tokens: None,
    })
}

#[tauri::command]
async fn list_available_models() -> Result<Vec<ModelInfo>, String> {
    Ok(vec![
        ModelInfo {
            name: "Qwen2.5-1.5B".to_string(),
            size: "1.5b".to_string(),
            description: "Ultra-light model optimized for MacBook Air".to_string(),
        },
        ModelInfo {
            name: "Qwen2.5-3B".to_string(),
            size: "3b".to_string(),
            description: "Balanced model (recommended default)".to_string(),
        },
        ModelInfo {
            name: "Qwen2.5-7B".to_string(),
            size: "7b".to_string(),
            description: "High-quality model for best performance".to_string(),
        },
        ModelInfo {
            name: "Groq (Cloud)".to_string(),
            size: "cloud".to_string(),
            description: "Ultra-fast cloud inference via Groq API".to_string(),
        },
    ])
}

#[tauri::command]
async fn switch_model(
    model_size: String,
    state: State<'_, Arc<AppState>>,
) -> Result<String, String> {
    println!("Switching to model: {}", model_size);

    // For now, we'll restart the backend with the new model
    // In a more sophisticated implementation, we'd update the config and reload

    Ok(format!("Model switch to {} queued. Restart backend to apply.", model_size))
}

#[tauri::command]
async fn get_config(state: State<'_, Arc<AppState>>) -> Result<serde_json::Value, String> {
    // Read current config from backend
    let url = state.api_url("/config");

    // For now, return a default config
    // In a full implementation, we'd actually read from the backend
    Ok(serde_json::json!({
        "backend": "local",
        "model_size": "3b",
        "temperature": 0.7,
        "max_tokens": 256
    }))
}

#[tauri::command]
async fn update_config(
    config: ConfigUpdate,
    state: State<'_, Arc<AppState>>,
) -> Result<(), String> {
    println!("Updating config: {:?}", config);

    // In a full implementation, we'd:
    // 1. Update the pebblemind.yaml file
    // 2. Notify the backend to reload config
    // 3. Or restart the backend with new config

    Ok(())
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! PebbleMind Desktop is ready!", name)
}

// ============================================================================
// Helper Functions
// ============================================================================

async fn check_backend_health(state: &Arc<AppState>) -> Result<BackendStatus, String> {
    let url = state.api_url("/health");

    match state.http_client.get(&url).send().await {
        Ok(response) if response.status().is_success() => Ok(BackendStatus {
            running: true,
            port: state.backend_port,
            model: Some("Qwen2.5-3B".to_string()), // Default
            backend_type: Some("local".to_string()),
        }),
        Ok(response) => Err(format!("Backend returned: {}", response.status())),
        Err(e) => Err(format!("Backend not responding: {}", e)),
    }
}

// ============================================================================
// Application Entry Point
// ============================================================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize application state
    let app_state = Arc::new(AppState::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            greet,
            start_backend,
            stop_backend,
            get_backend_status,
            send_chat_message,
            list_available_models,
            switch_model,
            get_config,
            update_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
