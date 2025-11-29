using System;
using System.Collections;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

[Serializable]
public class JournalEntryDTO
{
    public string content;
    public string ts_iso;          // ISO-8601 timestamp (UTC)
}

public class JournalSubmitter : MonoBehaviour
{
    [Header("UI")]
    [SerializeField] private TMP_InputField entryInput;
    [SerializeField] private TMP_Text charCounter;
    [SerializeField] private Button submitButton;

    [Tooltip("Tiny status text that says 'Saved ✓' when the entry is submitted.")]
    [SerializeField] private TMP_Text savedToast;

    [Header("API")]
    [SerializeField] private string baseUrl = "http://127.0.0.1:8000";
    [SerializeField] private string postPath = "/unity/journal/entry";
    [SerializeField] private string bearerToken = ""; // left blank; will be filled from AuthContext/PlayerPrefs

    [Header("Limits")]
    [SerializeField] private int maxCharacters = 2000;

    // Cache for toast fading
    private CanvasGroup toastCg;

    private void Awake()
    {
        // Safety checks to avoid null-ref surprises
        if (entryInput == null)
            Debug.LogWarning("[Journal] Entry Input not assigned in Inspector.");
        if (submitButton == null)
            Debug.LogWarning("[Journal] Submit Button not assigned in Inspector.");

        if (savedToast != null)
        {
            toastCg = savedToast.GetComponent<CanvasGroup>();
            if (toastCg == null) toastCg = savedToast.gameObject.AddComponent<CanvasGroup>();
            // Keep hidden on load
            savedToast.gameObject.SetActive(false);
            toastCg.alpha = 0f;
        }
    }

    private void Start()
    {
        // Pick up the token automatically (runtime-only; not serialized in scenes)
        if (string.IsNullOrEmpty(bearerToken))
        {
            // Prefer in-memory context (set during login)
            if (AuthContext.Instance != null && !string.IsNullOrEmpty(AuthContext.Instance.AccessToken))
            {
                bearerToken = AuthContext.Instance.AccessToken;
            }
            else
            {
                // Fallback to PlayerPrefs if available
                bearerToken = PlayerPrefs.GetString("access_token", "");
            }
        }

        // Wire the button to our handler
        if (submitButton != null)
            submitButton.onClick.AddListener(OnSubmitClicked);

        // Initialize / live-update the character counter
        UpdateCharCounter(entryInput != null ? entryInput.text : "");
        if (entryInput != null)
            entryInput.onValueChanged.AddListener(UpdateCharCounter);
    }

    private void UpdateCharCounter(string text)
    {
        if (charCounter == null) return;
        int len = string.IsNullOrEmpty(text) ? 0 : Mathf.Min(text.Length, maxCharacters);
        charCounter.text = $"{len}/{maxCharacters}";
    }

    private void OnSubmitClicked()
    {
        if (entryInput == null) return;

        string text = entryInput.text.Trim();

        // Basic validation
        if (string.IsNullOrEmpty(text))
        {
            Debug.LogWarning("[Journal] Cannot submit empty text.");
            return;
        }
        if (text.Length > maxCharacters)
        {
            Debug.LogWarning("[Journal] Text too long.");
            return;
        }

        // Disable while sending to prevent double-clicks
        if (submitButton != null) submitButton.interactable = false;

        var dto = new JournalEntryDTO
        {
            content = text,
            ts_iso = DateTime.UtcNow.ToString("o")  
        };

        StartCoroutine(PostEntry(dto));
    }

    private IEnumerator PostEntry(JournalEntryDTO dto)
    {
        string url = $"{baseUrl}{postPath}";
        string json = JsonUtility.ToJson(dto);

        using (var req = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST))
        {
            byte[] body = Encoding.UTF8.GetBytes(json);
            req.uploadHandler = new UploadHandlerRaw(body);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");

            // Attach Authorization header if we have a token
            if (!string.IsNullOrEmpty(bearerToken))
                req.SetRequestHeader("Authorization", $"Bearer {bearerToken}");

            req.timeout = 15;

            yield return req.SendWebRequest();

#if UNITY_2020_2_OR_NEWER
            bool netError = req.result == UnityWebRequest.Result.ConnectionError ||
                            req.result == UnityWebRequest.Result.ProtocolError;
#else
            bool netError = req.isNetworkError || req.isHttpError;
#endif

            bool ok = !netError && req.responseCode >= 200 && req.responseCode < 300;

            if (ok)
            {
                Debug.Log($"[Journal] Submitted OK: {req.downloadHandler.text}");

                // Success toast + clear input/counter
                if (savedToast != null)
                    StartCoroutine(ShowSavedToast("Saved ✓"));

                if (entryInput != null)
                    entryInput.text = "";

                UpdateCharCounter("");
            }
            else
            {
                Debug.LogError($"[Journal] Submit failed: {req.responseCode} {req.error} {req.downloadHandler.text}");

                // show a brief failure toast
                if (savedToast != null)
                    StartCoroutine(ShowSavedToast("Failed"));
                // We intentionally keep the text so the player can edit and retry
            }
        }

        // Re-enable after the request completes
        if (submitButton != null) submitButton.interactable = true;
    }

    private IEnumerator ShowSavedToast(string message)
    {
        if (savedToast == null) yield break;

        // Prep and show
        savedToast.text = message;
        savedToast.gameObject.SetActive(true);
        if (toastCg == null) toastCg = savedToast.GetComponent<CanvasGroup>();
        if (toastCg == null) toastCg = savedToast.gameObject.AddComponent<CanvasGroup>();
        toastCg.alpha = 0f;

        // Fade in
        float t = 0f;
        const float fadeDur = 0.12f;
        while (t < fadeDur)
        {
            t += Time.deltaTime;
            toastCg.alpha = Mathf.Lerp(0f, 1f, t / fadeDur);
            yield return null;
        }
        toastCg.alpha = 1f;

        // Hold visible
        yield return new WaitForSeconds(1.3f);

        // Fade out
        t = 0f;
        while (t < fadeDur)
        {
            t += Time.deltaTime;
            toastCg.alpha = Mathf.Lerp(1f, 0f, t / fadeDur);
            yield return null;
        }
        toastCg.alpha = 0f;
        savedToast.gameObject.SetActive(false);
    }
}
