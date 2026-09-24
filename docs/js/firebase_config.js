/**
 * Firebase Client Configuration & Loader for ICARUS Flight Operations
 * Supports Google Auth, Anonymous Station Auth, and Firestore Shared Realtime DB.
 */

// Default configuration template
// You can enter your credentials via Admin Console > "⚙ Firebase Config",
// or embed them here directly in window.FIREBASE_CONFIG.
const DEFAULT_FIREBASE_CONFIG = {
    apiKey: "",
    authDomain: "",
    projectId: "",
    storageBucket: "",
    messagingSenderId: "",
    appId: ""
};

// Retrieve custom credentials saved in localStorage, or window.FIREBASE_CONFIG, or DEFAULT_FIREBASE_CONFIG
function getFirebaseConfig() {
    try {
        const custom = localStorage.getItem("ICARUS_FIREBASE_CONFIG");
        if (custom) {
            const parsed = JSON.parse(custom);
            if (parsed && parsed.apiKey && parsed.projectId && !parsed.apiKey.includes("Placeholder")) {
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
        return Boolean(cfg && cfg.apiKey && cfg.projectId && cfg.apiKey.length > 5 && !cfg.apiKey.includes("Placeholder"));
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
