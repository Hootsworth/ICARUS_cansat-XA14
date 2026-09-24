/**
 * Firebase Client Configuration & Loader for ICARUS Flight Operations
 * Supports Google Auth, Anonymous Station Auth, and Firestore Shared Realtime DB.
 */

// Official Production Firebase Configuration (Default across all workstations)
const DEFAULT_FIREBASE_CONFIG = {
    apiKey: "AIzaSyBLbqh7mPrPAV3FVo46JnHE1iKM3SdfdyY",
    authDomain: "icarus-b8052.firebaseapp.com",
    projectId: "icarus-b8052",
    storageBucket: "icarus-b8052.firebasestorage.app",
    messagingSenderId: "783216515090",
    appId: "1:783216515090:web:ff32e5491d8c87058c20cb",
    measurementId: "G-G2S7E5NZFB"
};

// Retrieve credentials (uses default config automatically, or custom override if set)
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
