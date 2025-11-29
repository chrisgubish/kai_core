using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// UnityJournalAPI – Singleton: single source of truth for auth + API.
/// Keeps public signatures/events other systems (e.g., EmotionWeatherMapper) already use.
/// </summary>
/// 

public class UnityJournalAPI : MonoBehaviour
{
    // -------------------- Singleton --------------------
    public static UnityJournalAPI Instance { get; private set; }

    [Header("Backend")]
    [Tooltip("Base URL of your FastAPI backend (no trailing slash).")]
    [SerializeField] private string baseUrl = "http://127.0.0.1:8000";

    [Header("Debug")]
    [SerializeField] private bool enableDebugLogs = true;

    // PlayerPrefs keys
    private const string PREF_TOKEN   = "journal_access_token";
    private const string PREF_USER_ID = "journal_user_id";

    // Single source of truth (backing fields)
    private string _accessToken = "";
    private string _userId = "";
    // Token pieces saved separately to avoid "Bearer Bearer ..." bugs.
    private string _tokenType = "Bearer";     // default per RFC6750
    private string _accessTokenRaw = null;    // raw JWT only (no "Bearer ")


    // Public state
    public string AccessToken => _accessTokenRaw;                   // expose raw JWT (no "Bearer ")
    public string UserId      { get => _userId; private set => _userId = value; }
    public bool   IsAuthenticated => !string.IsNullOrEmpty(_accessTokenRaw);

    // -------------------- Events kept for other systems --------------------
    /// <summary>Raised after a journal entry is analyzed successfully.</summary>
    public event Action<EmotionAnalysisResult> OnEmotionAnalyzed;

    /// <summary>Raised after weather state is received from backend.</summary>
    public event Action<WeatherState> OnWeatherStateReceived;

    /// <summary>Raised whenever authentication state flips.</summary>
    public event Action<bool> OnAuthenticationChanged;

    /// <summary>Raised on transport/parse errors.</summary>
    public event Action<string> OnError;

    // -------------------- DTOs (kept stable) --------------------
    [Serializable]
    private class TokenResponse
    {
        public string access_token;
        public string token_type;
        public string user_id;
    }

    [Serializable]
    private class JournalPayload
    {
        public string content;
    }

    // Data returned by /journal/entry

    [Serializable]
    public class EmotionAnalysisResult
    {
        public string status;
        public string primary_emotion;
        public float intensity;
        public float confidence;
        public EmotionScores emotion_scores;                 // optional, may be null
        public EmotionCharacteristics emotion_characteristics; // contains valence/arousal
        public string category;
        public string timestamp;

        // Convenience read-only helpers so other scripts can keep using .valence/.arousal
        public float valence => emotion_characteristics != null ? emotion_characteristics.valence : 0f;
        public float arousal => emotion_characteristics != null ? emotion_characteristics.arousal : 0f;
    }

    [Serializable]
    public class EmotionScores
    {
        public float anger, disgust, fear, joy, neutral, sadness, surprise;
    }

    [Serializable]
    public class EmotionCharacteristics
    {
        public float valence;
        public float arousal;
    }

    [Serializable] public class EmotionPointDTO {
    public string timestamp;
    public string primary_emotion;
    public float valence;
    public float arousal;
    public float intensity;
    }

    [Serializable] public class EmotionSampleDTO {
        public string timestamp;
        public string primary_emotion;
        public float valence;
        public float arousal;
        public float intensity;
    }


    public static class JsonHelper
    {
        [Serializable]
        private class Wrapper<T> { public T[] Items; }

        public static T[] FromJson<T>(string json)
        {
            string wrapped = "{\"Items\":" + json + "}";
            var w = JsonUtility.FromJson<Wrapper<T>>(wrapped);
            return w.Items;
        }
    }

    [System.Serializable]
    public class JournalEntryResponse
    {
        // public string status;                    // e.g., "success"
        public string message;
        public int entry_id;
        public EmotionAnalysisResult emotion_analysis;   // <- the part we care about
        public string detail;
    }

    [Serializable]
    public class JournalListEntry
    {
        public string id;
        public string content;
        public string timestamp;
        public string date_formatted;
    }

    [Serializable]
    private class ItemsWrapper      { public JournalListEntry[] Items; }     // matches { "Items": [...] }
    [Serializable]
    private class EntriesWrapper    { public JournalListEntry[] entries; }   // matches { "entries": [...] }




    // Data returned by /unity/weather-state
    [Serializable]
    public class WeatherState
    {
        public string weather_type;
        public string emotion;
        public float intensity;
        public string description;  
        public string timestamp;    // string for simplicity
    }


    // --- HTTP helper: builds an authed JSON UnityWebRequest ---
    private UnityWebRequest BuildAuthedJsonRequest(string method, string path, string json)
    {
        // Must be logged in
        if (!IsAuthenticated) { Debug.LogWarning("[API] No token"); return null; }

        // Compose absolute URL
        var url = $"{baseUrl}{(path.StartsWith("/") ? "" : "/")}{path}";

        // Build request
        var req = new UnityWebRequest(url, method);
        byte[] bytes = System.Text.Encoding.UTF8.GetBytes(json ?? "{}");
        req.uploadHandler   = new UploadHandlerRaw(bytes);
        req.downloadHandler = new DownloadHandlerBuffer();

        // Ensure native handlers are disposed
        req.disposeUploadHandlerOnDispose   = true;
        req.disposeDownloadHandlerOnDispose = true;

        // Headers
        req.SetRequestHeader("Content-Type", "application/json");
        req.SetRequestHeader("Authorization", $"Bearer {_accessTokenRaw}");

        if (enableDebugLogs)
            Debug.Log($"[API] {method} {url} auth10='{_accessTokenRaw.Substring(0, Mathf.Min(10, _accessTokenRaw.Length))}'");

        return req;
    }



    // -------------------- Lifecycle (Singleton) --------------------
    private void Awake()
    {

        // Singleton guard
        if (Instance != null && Instance != this)
        {
            Debug.LogWarning("[UnityJournalAPI] Duplicate instance found, destroying this one.");
            Destroy(gameObject);
            return;
        }
        
        Instance = this;
        DontDestroyOnLoad(gameObject);

        // Normalize base URL (strip trailing slash)
        if (!string.IsNullOrEmpty(baseUrl) && baseUrl.EndsWith("/"))
            baseUrl = baseUrl.TrimEnd('/');

        // Load cached creds
        _accessTokenRaw = PlayerPrefs.GetString("access_token", "");
        if (string.IsNullOrWhiteSpace(_accessTokenRaw)) _accessTokenRaw = null;
        _userId = PlayerPrefs.GetString("user_id", "");
        _tokenType = "Bearer";

        // Validate token hasn't expired
        if (_accessTokenRaw != null)
        {
            if (IsTokenExpired(_accessTokenRaw))
            {
                if (enableDebugLogs)
                    Debug.LogWarning("[UnityJournalAPI] Cached token has expired. Clearing credentials.");
                _accessTokenRaw = null;
                _userId = "";
                PlayerPrefs.DeleteKey(PREF_TOKEN);
                PlayerPrefs.DeleteKey(PREF_USER_ID);
                PlayerPrefs.Save();
            }
        }

        if (enableDebugLogs)
        {
            Debug.Log($"[UnityJournalAPI] Token loaded from PlayerPrefs:");
            Debug.Log($"  - _accessTokenRaw length: {_accessTokenRaw?.Length ?? 0}");
            Debug.Log($"  - _accessTokenRaw (first 20 chars): {(_accessTokenRaw != null && _accessTokenRaw.Length > 20 ? _accessTokenRaw.Substring(0, 20) : _accessTokenRaw)}");
            Debug.Log($"  - _userId: {_userId}");
            Debug.Log($"  - IsAuthenticated: {IsAuthenticated}");
        }

        if (enableDebugLogs)
            Debug.Log($"[UnityJournalAPI] Awake. cachedToken={IsAuthenticated} userId={_userId}");

        SafeInvokeAuthChanged(IsAuthenticated);
    }

    private bool IsTokenExpired(string jwt)
    {
        if (string.IsNullOrEmpty(jwt)) return true;
        
        try
        {
            // JWT format: header.payload.signature
            var parts = jwt.Split('.');
            if (parts.Length != 3) return true;
            
            // Decode payload (base64url)
            var payload = parts[1];
            // Pad to multiple of 4
            payload = payload.PadRight(payload.Length + (4 - payload.Length % 4) % 4, '=');
            // Replace base64url chars with base64
            payload = payload.Replace('-', '+').Replace('_', '/');
            
            var payloadBytes = System.Convert.FromBase64String(payload);
            var payloadJson = System.Text.Encoding.UTF8.GetString(payloadBytes);
            
            // Parse JSON to find 'exp' claim
            var expMatch = System.Text.RegularExpressions.Regex.Match(payloadJson, @"""exp"":\s*(\d+)");
            if (!expMatch.Success) return false; // No exp claim = doesn't expire
            
            long expTimestamp = long.Parse(expMatch.Groups[1].Value);
            long currentTimestamp = (long)(System.DateTime.UtcNow - new System.DateTime(1970, 1, 1)).TotalSeconds;
            
            bool expired = currentTimestamp >= expTimestamp;
            if (enableDebugLogs && expired)
                Debug.LogWarning($"[UnityJournalAPI] Token expired. Exp: {expTimestamp}, Now: {currentTimestamp}");
            
            return expired;
        }
        catch (System.Exception e)
        {
            if (enableDebugLogs)
                Debug.LogWarning($"[UnityJournalAPI] Token expiration check failed: {e.Message}");
            return false; // Assume valid if can't parse
        }
    }

    [Serializable]
    private class RegisterPayload
    {
        public string username;
        public string password;
        public string email;
    }

    // ===== Public Register wrapper(s) =====
    public Coroutine Register(string username, string password, string email, Action<bool,string> onDone)
    {
        return StartCoroutine(RegisterCoroutine(username, password, email, onDone));
    }

    public Coroutine Register(string username, string password, string email)
    {
        return StartCoroutine(RegisterCoroutine(username, password, email, null));
    }

    // ===== The coroutine =====
    private IEnumerator RegisterCoroutine(string username, string password, string email, Action<bool,string> cb)
    {
        // 1) Build JSON
        var payloadObj = new RegisterPayload {
            username = (username ?? "").Trim(),
            password = (password ?? "").Trim(),
            email    = string.IsNullOrWhiteSpace(email) ? "user@example.com" : email.Trim()
        };
        var json = JsonUtility.ToJson(payloadObj);

        // 2) POST /register
        var url = $"{baseUrl}/register";
        using (var req = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST))
        {
            req.uploadHandler   = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");

            if (enableDebugLogs) Debug.Log($"[UnityJournalAPI] Register → {url} user='{payloadObj.username}' email='{payloadObj.email}'");
            yield return req.SendWebRequest();

            var ok = (req.result == UnityWebRequest.Result.Success) && (req.responseCode == 200);
            if (!ok)
            {
                var err = req.downloadHandler?.text ?? req.error;
                if (enableDebugLogs) Debug.LogError($"[UnityJournalAPI] Register failed: {req.responseCode} {err}");
                cb?.Invoke(false, string.IsNullOrEmpty(err) ? "Register failed" : err);
                yield break;
            }
        }

        // Auto-login right after successful registration
        if (enableDebugLogs) Debug.Log("[UnityJournalAPI] Register OK. Logging in...");
        yield return Login(payloadObj.username, payloadObj.password, (success, err) =>
        {
            if (!success && enableDebugLogs) Debug.LogError("[UnityJournalAPI] Auto-login after register failed: " + err);
            cb?.Invoke(success, err);
        });
    }


    // -------------------- Public API --------------------

    /// <summary>Check backend health. Calls onDone(true) on 200 OFK.</summary>
    public Coroutine CheckAPIHealth(Action<bool> onDone)
    {
        return StartCoroutine(CheckAPIHealthCo(onDone));
    }

    /// <summary>Login; stores token + userId; calls onDone(success, errorText).</summary>
    public Coroutine Login(string username, string password, Action<bool, string> onDone)
    {
        return StartCoroutine(LoginCoroutine(username, password, onDone));
    }

    /// <summary>Submit journal entry; on success returns backend JSON (analysis), also raises OnEmotionAnalyzed.</summary>
    public Coroutine SubmitJournalEntry(string content, Action<string> onDone)
    {
        return StartCoroutine(SubmitJournalEntryCoroutine(content, onDone));
    }

    // Overload expected by InGameJournal: allow calling without a callback.
    public Coroutine SubmitJournalEntry(string content)
    {
        // Reuse the existing coroutine; null means caller doesn't want a return string.
        return StartCoroutine(SubmitJournalEntryCoroutine(content, null));
    }

    /// <summary>Unity specific: get current mapped WeatherState.</summary>
    public Coroutine GetWeatherState(Action<WeatherState> onDone)
    {
        return StartCoroutine(GetWeatherStateCoroutine(onDone));
    }

    // Method expected by LoginSceneController: clear credentials and notify listeners.
    public void Logout()
    {
        if (enableDebugLogs) Debug.Log("[UnityJournalAPI] Logging out and clearing cached credentials.");

        _accessToken       = string.Empty;
        _userId            = string.Empty;
        _tokenType         = "Bearer";   // reset to default
        _accessTokenRaw    = null;       // clear raw token


        PlayerPrefs.DeleteKey(PREF_TOKEN);
        PlayerPrefs.DeleteKey(PREF_USER_ID);
        PlayerPrefs.Save();

        // Let anyone listening (e.g., UI) know we’re no longer authenticated
        SafeInvokeAuthChanged(false);
    }


    // -------------------- Coroutines --------------------
    private IEnumerator CheckAPIHealthCo(Action<bool> cb)
    {
        using (var req = UnityWebRequest.Get($"{baseUrl}/health"))
        {
            req.downloadHandler = new DownloadHandlerBuffer();
            yield return req.SendWebRequest();

            bool ok = req.result == UnityWebRequest.Result.Success && req.responseCode == 200;
            if (enableDebugLogs) Debug.Log($"[UnityJournalAPI] /health -> {req.responseCode} ok={ok}");
            cb?.Invoke(ok);
        }
    }

    private IEnumerator LoginCoroutine(string username, string password, Action<bool, string> cb)
    {
        if (enableDebugLogs)
            Debug.Log($"[UnityJournalAPI] Logging in... user='{username}'");

        var form = new WWWForm();
        form.AddField("username", username ?? "");
        form.AddField("password", password ?? "");

        using (var req = UnityWebRequest.Post($"{baseUrl}/token", form))
        {
            req.downloadHandler = new DownloadHandlerBuffer();
            yield return req.SendWebRequest();

            var ok = (req.result == UnityWebRequest.Result.Success) && (req.responseCode == 200);
            if (!ok)
            {
                var err = req.downloadHandler?.text ?? req.error;
                if (enableDebugLogs) Debug.LogError($"[UnityJournalAPI] Login failed: {req.responseCode} {err}");
                cb?.Invoke(false, err);
                yield break;
            }

            TokenResponse tok = null;
            try
            {
                tok = JsonUtility.FromJson<TokenResponse>(req.downloadHandler.text);
            }
            catch (Exception e)
            {
                if (enableDebugLogs) Debug.LogError($"[UnityJournalAPI] Token parse error: {e.Message}");
            }

            if (tok == null || string.IsNullOrEmpty(tok.access_token))
            {
                cb?.Invoke(false, "No access_token in response");
                yield break;
            }

            // Save token pieces
            _tokenType      = string.IsNullOrEmpty(tok.token_type) ? "Bearer" : tok.token_type.Trim();
            _accessTokenRaw = tok.access_token?.Trim();

            // If backend already prefixed with "Bearer ", strip it off so we don't send "Bearer Bearer ..."
            if (!string.IsNullOrEmpty(_accessTokenRaw) &&
                _accessTokenRaw.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
            {
                _accessTokenRaw = _accessTokenRaw.Substring("Bearer ".Length).Trim();
            }

            // Keep user id
            UserId = tok.user_id ?? "";

            PlayerPrefs.SetString(PREF_TOKEN,   _accessTokenRaw ?? "");
            PlayerPrefs.SetString(PREF_USER_ID, UserId);
            PlayerPrefs.Save();

            if (enableDebugLogs)
            {
                Debug.Log($"[UnityJournalAPI] Token saved:");
                Debug.Log($"  - _accessTokenRaw length: {_accessTokenRaw?.Length ?? 0}");
                Debug.Log($"  - PlayerPrefs value: {PlayerPrefs.GetString(PREF_TOKEN, "MISSING")}");
            }


            if (enableDebugLogs)
                Debug.Log($"[UnityJournalAPI] Login success. token len={AccessToken.Length} userId={UserId}");

            SafeInvokeAuthChanged(true);
            cb?.Invoke(true, null);
        }
    }

    private IEnumerator SubmitJournalEntryCoroutine(string content, System.Action<string> cb)
    {
        // Guard + get a trimmed local token snapshot (raw JWT only)
    var token = AccessToken;
    token = string.IsNullOrWhiteSpace(token) ? null : token.Trim();

    if (string.IsNullOrEmpty(token))
    {
        if (enableDebugLogs)
            Debug.LogError("[UnityJournalAPI] SubmitJournalEntry: no access token. Call Login first.");
        cb?.Invoke(null);
        yield break;
    }

    if (enableDebugLogs)
    {
        Debug.Log($"[UnityJournalAPI] Submit auth header:");
        Debug.Log($"  - token length: {token.Length}");
        Debug.Log($"  - token (first 50 chars): {token.Substring(0, Math.Min(50, token.Length))}");
    }

        // JSON body (use the method parameter 'content' and a serializable payload)
        var payloadObj = new JournalPayload { content = content ?? string.Empty };
        var json       = JsonUtility.ToJson(payloadObj);
        var bodyBytes  = System.Text.Encoding.UTF8.GetBytes(json);

        // Request (dispose handlers to avoid leaks)
        var url = $"{baseUrl}/journal/entry";
        using (var req = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST))
        {
            req.uploadHandler   = new UploadHandlerRaw(bodyBytes);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.disposeUploadHandlerOnDispose   = true;
            req.disposeDownloadHandlerOnDispose = true;

            // Headers
            req.SetRequestHeader("Content-Type", "application/json");
            req.SetRequestHeader("Authorization", $"Bearer {token}");

            if (enableDebugLogs)
                Debug.Log($"[UnityJournalAPI] POST {url}, authLen={token.Length}, bodyLen={bodyBytes.Length}");

            // Send
            yield return req.SendWebRequest();

            // Handle response
            if (req.responseCode == 401)
            {
                if (enableDebugLogs)
                    Debug.LogWarning($"[UnityJournalAPI] 401 Unauthorized. body='{req.downloadHandler?.text}'");
                SafeInvokeAuthChanged(false);
                cb?.Invoke(null);
                yield break;
            }

            var ok = (req.result == UnityWebRequest.Result.Success) && (req.responseCode == 200);
            if (!ok)
            {
                var authHdr = req.GetResponseHeader("www-authenticate");
                if (enableDebugLogs)
                    Debug.LogError($"[UnityJournalAPI] Submit failed: {req.responseCode} {req.error} www-auth='{authHdr}' body='{req.downloadHandler?.text}'");
                cb?.Invoke(null);
                yield break;
            }

            var body = req.downloadHandler.text;
            if (enableDebugLogs) Debug.Log($"[UnityJournalAPI] Submit ok: {body}");

            // Parse server wrapper -> raise emotion event
            try
            {
                var wrapper = JsonUtility.FromJson<JournalEntryResponse>(body);
                var analysis = wrapper?.emotion_analysis;

                if (analysis != null && !string.IsNullOrEmpty(analysis.primary_emotion))
                    {
                        OnEmotionAnalyzed?.Invoke(analysis);
                    }
                else
                {
                    if (enableDebugLogs)
                        Debug.LogWarning("[UnityJournalAPI] JournalEntryResponse missing emotion_analysis or primary_emotion");
                }
                }
            catch (Exception e)
            {
                if (enableDebugLogs)
                    Debug.LogWarning($"[UnityJournalAPI] Parse warning: {e.Message}");
            }

            cb?.Invoke(body);
        }
    }

    public Coroutine GetJournalEntries(int limit, int offset, Action<JournalListEntry[]> onDone)
    {
        return StartCoroutine(GetJournalEntriesCoroutine(limit, offset, onDone));
    }

    private IEnumerator GetJournalEntriesCoroutine(int limit, int offset, Action<JournalListEntry[]> cb)
    {
        var token = AccessToken;          
        token = string.IsNullOrWhiteSpace(token) ? null : token.Trim();

        if (string.IsNullOrEmpty(token))
        {
            Debug.LogError("[UnityJournalAPI] GetJournalEntries: not authenticated or missing user id.");
            cb?.Invoke(null);
            yield break;
        }

    // sanitize
        limit  = Mathf.Max(1, limit);
        offset = Mathf.Max(0, offset);

        var url = $"{baseUrl}/journal/entries?limit={limit}&offset={offset}";


        using (var req = UnityWebRequest.Get(url))
        {
            req.SetRequestHeader("Authorization", $"Bearer {token}");
            req.downloadHandler = new DownloadHandlerBuffer();

            if (enableDebugLogs)
            {
                var head10 = token.Substring(0, Mathf.Min(10, token.Length));
                Debug.Log($"[Entries] Authorization: Bearer {head10}...");
            }


            yield return req.SendWebRequest();

            if (req.responseCode == 401)
            {
                Debug.LogWarning($"[UnityJournalAPI] Entries 401 Unauthorized. body='{req.downloadHandler?.text}'");
                SafeInvokeAuthChanged(false);       // notify listeners (e.g., UI -> show login)
                cb?.Invoke(null);
                yield break;
            }



            if (req.result != UnityWebRequest.Result.Success || req.responseCode != 200)
            {
                Debug.LogError($"[UnityJournalAPI] Entries fetch failed: {req.responseCode} {req.error} body='{req.downloadHandler?.text}'"); 
                cb?.Invoke(null);
                yield break;
            }

            var json = req.downloadHandler.text ?? "";
            Debug.Log($"[Entries] HTTP 200. Raw JSON len={json.Length}");

            JournalListEntry[] data = null;

            try
            {
                var trimmed = json.TrimStart();

                // Case 1: API returns a top-level array: [...]
                if (trimmed.StartsWith("["))
                {
                    data = JsonHelper.FromJson<JournalListEntry>(json);
                }
                else
                {
                    // Case 2: object wrapper
                    // Prefer { "Items": [...] } if present...
                    var wItems = JsonUtility.FromJson<ItemsWrapper>(json);
                    if (wItems != null && wItems.Items != null)
                        data = wItems.Items;
                    else
                    {
                        // ...fallback to { "entries": [...] }
                        var wEntries = JsonUtility.FromJson<EntriesWrapper>(json);
                        if (wEntries != null && wEntries.entries != null)
                            data = wEntries.entries;
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogError("[UnityJournalAPI] Parse error: " + e.Message);
            }
            
            Debug.Log($"[Entries] Parsed count={(data?.Length ?? 0)}");
            cb?.Invoke(data ?? Array.Empty<JournalListEntry>());

        }
    }

    private IEnumerator GetJson<T>(string path, Action<T> cb)
    {
        // Guard
        var token = AccessToken;
        token = string.IsNullOrWhiteSpace(token) ? null : token.Trim();
        if (string.IsNullOrEmpty(token)) { Debug.LogError("[API] GetJson: no token"); cb?.Invoke(default); yield break; }

        // Build URL
        var url = $"{baseUrl}{(path.StartsWith("/") ? "" : "/")}{path}";

        using (var req = UnityWebRequest.Get(url))
        {
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Authorization", $"Bearer {token}");
            req.SetRequestHeader("Accept", "application/json");

            yield return req.SendWebRequest();

            if (req.responseCode == 401) { Debug.LogWarning($"[API] 401 {url}"); SafeInvokeAuthChanged(false); cb?.Invoke(default); yield break; }
            if (req.result != UnityWebRequest.Result.Success || req.responseCode != 200)
            { Debug.LogError($"[API] GET fail {req.responseCode} {url} body='{req.downloadHandler?.text}'"); cb?.Invoke(default); yield break; }

            T data = default;
            try { data = JsonUtility.FromJson<T>(req.downloadHandler.text); }
            catch (Exception e) { Debug.LogError($"[API] Parse error: {e.Message}"); }

            cb?.Invoke(data);
        }
    }

    private IEnumerator GetJsonArray<T>(string path, Action<T[]> cb)
    {
        var token = AccessToken;
        token = string.IsNullOrWhiteSpace(token) ? null : token.Trim();
        if (string.IsNullOrEmpty(token)) { Debug.LogError("[API] GetJsonArray: no token"); cb?.Invoke(null); yield break; }

        var url = $"{baseUrl}{(path.StartsWith("/") ? "" : "/")}{path}";

        using (var req = UnityWebRequest.Get(url))
        {
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Authorization", $"Bearer {token}");
            req.SetRequestHeader("Accept", "application/json");

            yield return req.SendWebRequest();

            if (req.responseCode == 401) { Debug.LogWarning($"[API] 401 {url}"); SafeInvokeAuthChanged(false); cb?.Invoke(null); yield break; }
            if (req.result != UnityWebRequest.Result.Success || req.responseCode != 200)
            { Debug.LogError($"[API] GET fail {req.responseCode} {url} body='{req.downloadHandler?.text}'"); cb?.Invoke(null); yield break; }

            // Unity's JsonUtility cannot parse a top-level array; wrap/unwrap.
            T[] data = null;
            try { data = JsonHelper.FromJson<T>(req.downloadHandler.text); }
            catch (Exception e) { Debug.LogError($"[API] Parse array error: {e.Message}"); }

            cb?.Invoke(data ?? Array.Empty<T>());
        }
    }

    public void GetMoodSamples(int days, Action<EmotionPointDTO[]> onDone)
    {
        StartCoroutine(GetJsonArray<EmotionPointDTO>($"/mood/samples?days={days}", onDone));
    }

    public void GetCurrentEmotion(Action<EmotionSampleDTO> onDone)
    {
        StartCoroutine(GetJson<EmotionSampleDTO>("/emotion/current", onDone));
    }

    private IEnumerator GetWeatherStateCoroutine(Action<WeatherState> cb)
    {
        // Get token
        var token = AccessToken;
        token = string.IsNullOrWhiteSpace(token) ? null : token.Trim();
        if (string.IsNullOrEmpty(token))
        {
            Debug.LogError("[UnityJournalAPI] GetWeatherState: not authenticated (no token)");
            cb?.Invoke(null);
            yield break;
        }

        var url = $"{baseUrl}/unity/weather-state";

        using (var req = UnityWebRequest.Get(url))
        {
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Authorization", $"Bearer {token}");
            req.SetRequestHeader("Accept", "application/json");

            yield return req.SendWebRequest();

            if (req.responseCode == 401)
            {
                Debug.LogWarning($"[UnityJournalAPI] Weather state 401 Unauthorized. body='{req.downloadHandler?.text}'");
                SafeInvokeAuthChanged(false);
                cb?.Invoke(null);
                yield break;
            }

            var ok = (req.result == UnityWebRequest.Result.Success) && (req.responseCode == 200);
            if (!ok)
            {
                if (enableDebugLogs)
                    Debug.LogError($"[UnityJournalAPI] Weather state failed: {req.responseCode} {req.error} body='{req.downloadHandler?.text}'");
                cb?.Invoke(null);
                yield break;
            }

            WeatherState state = null;
            try
            {
                state = JsonUtility.FromJson<WeatherState>(req.downloadHandler.text);
            }
            catch (Exception e)
            {
                if (enableDebugLogs) Debug.LogError($"[UnityJournalAPI] Weather parse error: {e.Message}");
            }

            if (state != null)
                OnWeatherStateReceived?.Invoke(state);

            cb?.Invoke(state);
        }
    }

    private void SafeInvokeAuthChanged(bool isAuthed)
    {
        try { OnAuthenticationChanged?.Invoke(isAuthed); }
        catch (Exception e) { if (enableDebugLogs) Debug.LogError(e); }
    }
}
