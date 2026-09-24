/**
 * Firebase Client Configuration & Loader for ICARUS Flight Operations
 * Supports Google Auth, Anonymous Station Auth, and Firestore Shared Realtime DB.
 */

// Default configuration template
const DEFAULT_FIREBASE_CONFIG = {
    apiKey: "AIzaSyDemoTelemetryKeyPlaceholder2027",
    authDomain: "icarus-telemetry-rvu.firebaseapp.com",
    projectId: "icarus-telemetry-rvu",
    storageBucket: "icarus-telemetry-rvu.appspot.com",
    messagingSenderId: "109876543210",
    appId: "1:109876543210:web:9876543210abcdef"
};

// Retrieve any custom credentials saved in localStorage
function getFirebaseConfig() {
    try {
        const custom = localStorage.getItem("ICARUS_FIREBASE_CONFIG");
        if (custom) {
            const parsed = JSON.parse(custom);
            if (parsed && parsed.apiKey && !parsed.apiKey.includes("Placeholder")) {
                return parsed;
            }
        }
    } catch (e) {
        console.warn("[Firebase] Error parsing custom config:", e);
    }
    return window.FIREBASE_CONFIG || DEFAULT_FIREBASE_CONFIG;
}

window.IcarusFirebase = {
    app: null,
    auth: null,
    db: null,
    isInitialized: false,
    isConfigured() {
        const cfg = getFirebaseConfig();
        return cfg && cfg.apiKey && !cfg.apiKey.includes("Placeholder");
    },
    saveConfig(cfg) {
        localStorage.setItem("ICARUS_FIREBASE_CONFIG", JSON.stringify(cfg));
        window.location.reload();
    },
    clearConfig() {
        localStorage.removeItem("ICARUS_FIREBASE_CONFIG");
        window.location.reload();
    },
    getConfig: getFirebaseConfig
};
