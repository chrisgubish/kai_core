using System;
using System.Collections;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using TMPro;

namespace KaiProject
{
    /// <summary>
    /// Manages the login/registration scene before game starts.
    /// Handles authentication, auto-login for returning users, and scene transitions.
    /// </summary>
    /// 
    
    public class LoginSceneController : MonoBehaviour
    {
        #region UI References
        [Header("UI Elements - Login")]
        [Tooltip("Username input field")]
        public TMP_InputField usernameInput;
        
        [Tooltip("Password input field")]
        public TMP_InputField passwordInput;
        
        [Tooltip("Login button")]
        public Button loginButton;
        
        [Tooltip("Register button")]
        public Button registerButton;
        
        [Tooltip("Status/error message display")]
        public TextMeshProUGUI statusText;
        
        [Tooltip("Loading indicator (optional)")]
        public GameObject loadingPanel;

        [Header("UI Elements - Registration Mode")]
        [Tooltip("Panel to show when in registration mode")]
        public GameObject registrationPanel;
        
        [Tooltip("Switch to registration mode button")]
        public Button switchToRegisterButton;
        
        [Tooltip("Switch back to login mode button")]
        public Button switchToLoginButton;
        
        [Header("Scene Configuration")]
        [Tooltip("Name of the main game scene to load after authentication")]
        public string mainGameSceneName = "OpeningScene";
        
        [Header("Backend Connection")]
        [Tooltip("Check backend health on startup")]
        public bool checkBackendHealth = true;
        
        [Header("Auto-Login")]
        [Tooltip("Automatically login returning users with cached credentials")]
        public bool enableAutoLogin = true;
        
        [Tooltip("Delay before auto-login (seconds)")]
        public float autoLoginDelay = 0.5f;
        #endregion

        #region Private Fields
        private UnityJournalAPI api;
        private bool isRegistrationMode = false;
        private bool isProcessing = false;
        
        [SerializeField] private SceneRef targetScene;  // drag the SceneRef here

        #endregion

        #region Unity Lifecycle

        private void Awake()
        {
            api = UnityJournalAPI.Instance;

            if (api == null)
            {
                var existing = FindObjectOfType<UnityJournalAPI>();
                if (existing != null)
                {
                    api = existing;
                    Debug.Log("[LoginScene] Found existing UnityJournalAPI.");
                }
                else
                {
                    GameObject apiObject = new GameObject("JournalAPIManager");
                    api = apiObject.AddComponent<UnityJournalAPI>();
                    DontDestroyOnLoad(apiObject);
                    Debug.Log("[LoginScene] Created new JournalAPIManager.");
                }
            }
        }

        void Start()
        {
            // Find or create API manager
            SetupAPIManager();
            
            // Setup UI listeners
            SetupUIListeners();
            
            // Hide loading panel initially
            if (loadingPanel != null)
                loadingPanel.SetActive(false);
            
            // Start with login mode
            SetLoginMode();
            
            // Check backend health
            if (checkBackendHealth)
            {
                CheckBackendConnection();
            }
            
            // Auto-login for returning users
            if (enableAutoLogin)
            {
                StartCoroutine(AttemptAutoLogin());
            }
        }
        #endregion

        #region Setup
        private void SetupAPIManager()
        {
            // Try to find existing API manager
            api = FindObjectOfType<UnityJournalAPI>();
            
            // If not found, create one
            if (api == null)
            {
                GameObject apiObject = new GameObject("JournalAPIManager");
                api = apiObject.AddComponent<UnityJournalAPI>();
                DontDestroyOnLoad(apiObject);
                
                Debug.Log("[LoginScene] Created new JournalAPIManager");
            }
            else
            {
                // Make sure it persists between scenes
                DontDestroyOnLoad(api.gameObject);
            }
            
            // Subscribe to events (OnError event no longer exists in new API)
            api.OnAuthenticationChanged += OnAuthenticationChanged;
        }

        private void SetupUIListeners()
        {
            // Main buttons
            if (loginButton != null)
                loginButton.onClick.AddListener(OnLoginButtonClicked);
            
            if (registerButton != null)
                registerButton.onClick.AddListener(OnRegisterButtonClicked);
            
            // Mode switch buttons
            if (switchToRegisterButton != null)
                switchToRegisterButton.onClick.AddListener(() => SetRegistrationMode());
            
            if (switchToLoginButton != null)
                switchToLoginButton.onClick.AddListener(() => SetLoginMode());
            
            // Enter key support
            if (passwordInput != null)
            {
                passwordInput.onSubmit.AddListener((text) => {
                    if (isRegistrationMode)
                        OnRegisterButtonClicked();
                    else
                        OnLoginButtonClicked();
                });
            }
        }
        #endregion

        #region Auto-Login
        private IEnumerator AttemptAutoLogin()
        {
            // Wait a moment for UI to initialize
            yield return new WaitForSecondsRealtime(autoLoginDelay);
            
            // Check if user has cached credentials
            if (api.IsAuthenticated)
            {
                bool _hcDone = false;
                bool _hcOK = false;

                bool done = false;
                bool ok = false;
                api.CheckAPIHealth(isHealthy => { ok = isHealthy; done = true; });

                float t = 0f, limit = 5f;          // 5s timeout
                while (!done && t < limit) { t += Time.unscaledDeltaTime; yield return null; }
                if (!done) { ok = false; }         // treat timeout as failure

                if (_hcOK)
                {
                    var nameToLoad = (targetScene != null && !string.IsNullOrEmpty(targetScene.sceneName))
                    ? targetScene.sceneName
                    : mainGameSceneName;
                    Debug.Log($"[Login] Success. Loading '{nameToLoad}' …");
                    StartCoroutine(LoadGameAfterDelay(1.5f, nameToLoad));
                }
                else
                {
                    UpdateStatus("Session expired. Please login again.", Color.yellow);
                    api.Logout();
                    ShowLoading(false);
                }
            }
        }
        #endregion

        #region Authentication Actions
        private void OnLoginButtonClicked()
        {
            if (isProcessing) return;
            
            string username = usernameInput.text.Trim();
            string password = passwordInput.text;
            
            // Validation
            if (string.IsNullOrEmpty(username))
            {
                UpdateStatus("Please enter a username", Color.red);
                return;
            }
            
            if (string.IsNullOrEmpty(password))
            {
                UpdateStatus("Please enter a password", Color.red);
                return;
            }
            
            if (username.Length < 3)
            {
                UpdateStatus("Username must be at least 3 characters", Color.red);
                return;
            }
            
            // Start login
            isProcessing = true;
            ShowLoading(true);
            DisableInputs(true);
            UpdateStatus("Logging in...", Color.cyan);
            
            api.Login(username, password, OnLoginComplete);
        }

        private void OnRegisterButtonClicked()
        {
            if (isProcessing) return;

            string username = usernameInput.text.Trim();
            string password = passwordInput.text;

            // Basic validation
            if (string.IsNullOrEmpty(username)) { UpdateStatus("Please enter a username", Color.red); return; }
            if (string.IsNullOrEmpty(password)) { UpdateStatus("Please enter a password", Color.red); return; }
            if (username.Length < 3)            { UpdateStatus("Username must be at least 3 characters", Color.red); return; }
            if (password.Length < 6)            { UpdateStatus("Password must be at least 6 characters", Color.red); return; }

            isProcessing = true;
            ShowLoading(true);
            DisableInputs(true);
            UpdateStatus("Creating account...", Color.cyan);

            // If you don’t have an email field, send a placeholder or generate one.
            var email = $"{username}@example.com";

            api.Register(username, password, email, (ok, err) =>
            {
                isProcessing = false;
                ShowLoading(false);
                DisableInputs(false);

                if (ok)
                {
                    // UnityJournalAPI auto-logs in after a successful /register.
                    UpdateStatus("Account created! Logging in…", Color.green);
                    // Optionally move to the game scene like you do after login:

                    var nameToLoad = (targetScene != null && !string.IsNullOrEmpty(targetScene.sceneName))
                        ? targetScene.sceneName
                        : mainGameSceneName;
                    StartCoroutine(LoadGameAfterDelay(1.5f, nameToLoad));
                }
                else
                {
                    UpdateStatus($"Registration failed: {err}", Color.red);
                    if (passwordInput) { passwordInput.text = ""; passwordInput.Select(); }
                }
            });
        }

        #endregion

        #region Callbacks
        private void OnLoginComplete(bool success, string message)
        {
            isProcessing = false;
            ShowLoading(false);
            DisableInputs(false);

            if (success)
            {
                UpdateStatus("Login successful! Loading game...", Color.green);

                // Store access token if available, but never block on it
                try
                {
                    if (api != null && !string.IsNullOrEmpty(api.AccessToken))
                    {
                        // AuthContext may not be in this scene yet — guard it
                        var auth = AuthContext.Instance;
                        if (auth != null)
                        {
                            auth.AccessToken = api.AccessToken;
                        }
                        else
                        {
                            Debug.LogWarning("[LoginScene] AuthContext.Instance is null; will rely on PlayerPrefs.");
                        }

                        PlayerPrefs.SetString("access_token", api.AccessToken);
                        PlayerPrefs.Save();
                        Debug.Log("[LoginScene] Access token saved successfully.");
                    }
                    else
                    {
                        Debug.LogWarning("[LoginScene] API or AccessToken is null after login.");
                    }
                }
                catch (Exception e)
                {
                    Debug.LogWarning($"[LoginScene] Non-fatal error while caching token: {e.Message}");
                }

                // Always proceed to load the game scene
                // var nameToLoad = targetScene != null ? targetScene.sceneName : mainGameSceneName;
                var nameToLoad = (targetScene != null && !string.IsNullOrEmpty(targetScene.sceneName))
                    ? targetScene.sceneName
                    : mainGameSceneName;
                Debug.Log($"[Login] Success. Loading '{nameToLoad}' …");
                StartCoroutine(LoadGameAfterDelay(0.25f, nameToLoad));
            }
            else
            {
                UpdateStatus($"Login failed: {message}", Color.red);

                if (passwordInput != null)
                {
                    passwordInput.text = "";
                    passwordInput.Select();
                }
            }
        }

        private void OnAuthenticationChanged(bool isAuthenticated)
        {
            if (isAuthenticated)
            {
                Debug.Log("[LoginScene] Authentication successful");
            }
            else
            {
                Debug.Log("[LoginScene] Authentication cleared");
            }
        }
        #endregion

        #region UI Mode Switching
        private void SetLoginMode()
        {
            isRegistrationMode = false;
            
            if (registrationPanel != null)
                registrationPanel.SetActive(false);
            
            if (loginButton != null)
                loginButton.gameObject.SetActive(true);
            
            if (registerButton != null)
                registerButton.gameObject.SetActive(false);
            
            if (switchToRegisterButton != null)
                switchToRegisterButton.gameObject.SetActive(true);
            
            if (switchToLoginButton != null)
                switchToLoginButton.gameObject.SetActive(false);
            
            UpdateStatus("Enter your credentials to login", Color.white);
            
            // Clear fields
            if (usernameInput != null) usernameInput.text = "";
            if (passwordInput != null) passwordInput.text = "";
        }

        private void SetRegistrationMode()
        {
            isRegistrationMode = true;
            
            if (registrationPanel != null)
                registrationPanel.SetActive(true);
            
            if (loginButton != null)
                loginButton.gameObject.SetActive(false);
            
            if (registerButton != null)
                registerButton.gameObject.SetActive(true);
            
            if (switchToRegisterButton != null)
                switchToRegisterButton.gameObject.SetActive(false);
            
            if (switchToLoginButton != null)
                switchToLoginButton.gameObject.SetActive(true);
            
            UpdateStatus("Create a new account", Color.white);
            
            // Clear fields
            if (usernameInput != null) usernameInput.text = "";
            if (passwordInput != null) passwordInput.text = "";
        }
        #endregion

        #region Backend Health Check

        private void CheckBackendConnection()
        {
            UpdateStatus("Checking backend connection...", Color.yellow);
            
            // Use the new HealthCheck coroutine
            api.CheckAPIHealth((isHealthy) => {
                if (isHealthy)
                {
                    UpdateStatus("Backend connected. Ready to login!", Color.green);
                }
                else
                {
                    UpdateStatus("Warning: Cannot reach backend server. Make sure it's running at http://127.0.0.1:8000", Color.red);
                }
            });
        }
        #endregion

        #region Scene Transition
        private IEnumerator LoadGameAfterDelay(float delaySeconds, string sceneName)
        {
            // Wait independent of Time.timeScale
            yield return new WaitForSecondsRealtime(delaySeconds);

            // Ensure not paused
            Time.timeScale = 1f;

            // Fail fast if scene isn’t in Build Settings
            if (!Application.CanStreamedLevelBeLoaded(sceneName))
            {
                Debug.LogError($"[Login] Scene '{sceneName}' not found in Build Settings.");
                PrintBuildScenes();
                yield break;
            }

            // Bulletproof async load
            var op = SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Single);
            op.allowSceneActivation = true;
            while (!op.isDone) yield return null;
        }


        private static void PrintBuildScenes()
        {
            for (int i = 0; i < SceneManager.sceneCountInBuildSettings; i++)
            {
                var path = SceneUtility.GetScenePathByBuildIndex(i);
                Debug.Log($"[Build] {i}: {System.IO.Path.GetFileNameWithoutExtension(path)} -> {path}");
            }
        }
        #endregion

        #region UI Helpers
        private void UpdateStatus(string message, Color color)
        {
            if (statusText != null)
            {
                statusText.text = message;
                statusText.color = color;
            }
            
            Debug.Log($"[LoginScene] Status: {message}");
        }

        private void ShowLoading(bool show)
        {
            if (loadingPanel != null)
            {
                loadingPanel.SetActive(show);
            }
        }

        private void DisableInputs(bool disable)
        {
            if (usernameInput != null)
                usernameInput.interactable = !disable;
            
            if (passwordInput != null)
                passwordInput.interactable = !disable;
            
            if (loginButton != null)
                loginButton.interactable = !disable;
            
            if (registerButton != null)
                registerButton.interactable = !disable;
            
            if (switchToRegisterButton != null)
                switchToRegisterButton.interactable = !disable;
            
            if (switchToLoginButton != null)
                switchToLoginButton.interactable = !disable;
        }
        #endregion

        #region Cleanup
        private void OnDestroy()
        {
            // Unsubscribe from events (OnError event no longer exists)
            if (api != null)
            {
                api.OnAuthenticationChanged -= OnAuthenticationChanged;
            }
        }
        #endregion

        #region Public Methods for Testing
        /// <summary>
        /// Force a backend health check (useful for testing)
        /// </summary>
        public void RefreshBackendStatus()
        {
            CheckBackendConnection();
        }

        /// <summary>
        /// Clear any cached credentials (useful for testing)
        /// </summary>
        public void ClearCredentials()
        {
            if (api != null)
            {
                api.Logout();
                UpdateStatus("Credentials cleared. Please login.", Color.yellow);
            }
        }
        #endregion
    }
}