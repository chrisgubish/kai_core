using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System;

public class InGameJournal : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private TMP_InputField journalInputField;
    [SerializeField] private Button submitButton;
    [SerializeField] private TMP_Text characterCountText;
    [SerializeField] private GameObject journalPanel; // purely referenced, no toggle logic here

    [Header("Settings")]
    [SerializeField] private int  maxCharacters      = 2000;
    [SerializeField] private bool pauseGameWhenOpen = false; 

    [Header("API Reference (optional)")]
    [SerializeField] private UnityJournalAPI journalAPI;    

    [Header("Debug")]
    [SerializeField] private bool     enableDebugLogs = true;
    [SerializeField] private TMP_Text  toastText;           

    // ─────────────────────────────────────────────────────────────────────────────

    private void Awake()
    {
        // If Journal Panel wasn’t dragged in, try to find it by name once.
        if (!journalPanel)
        {
            var candidate = GameObject.Find("JournalPanel");
            if (candidate) journalPanel = candidate;
        }

        // Only search WITHIN the journal panel so we don't grab unrelated UI.
        if (journalPanel)
        {
            var root = journalPanel.transform;

            if (!journalInputField)
                journalInputField = root.GetComponentInChildren<TMPro.TMP_InputField>(true);

            if (!submitButton)
            {
                // Bind specifically to the actual SubmitButton under the panel
                foreach (var b in root.GetComponentsInChildren<UnityEngine.UI.Button>(true))
                {
                    if (b.name.Equals("SubmitButton", StringComparison.OrdinalIgnoreCase))
                    {
                        submitButton = b;
                        break;
                    }
                }
            }

            if (!characterCountText)
            {
                foreach (var t in root.GetComponentsInChildren<TMPro.TMP_Text>(true))
                {
                    var n = t.name.ToLowerInvariant();
                    if (n.Contains("char") || n.Contains("count"))
                    {
                        characterCountText = t;
                        break;
                    }
                }
            }
        }

        // Get a valid API reference (singleton first, then scene lookup).
        if (!journalAPI)
            journalAPI = UnityJournalAPI.Instance;
        if (!journalAPI)
            journalAPI = FindObjectOfType<UnityJournalAPI>(true);

        if (!journalAPI && enableDebugLogs)
            Debug.LogError("[InGameJournal] JournalAPI reference not set and could not be found.");
    }

    private void Start()
    {
        // DO NOT toggle/show/hide the panel here. JournalPanelController owns that.
        if (journalInputField)
        {
            journalInputField.characterLimit = maxCharacters > 0 ? maxCharacters : 0;
            journalInputField.onValueChanged.AddListener(OnInputChanged);
        }

        if (submitButton)
            submitButton.onClick.AddListener(OnSubmitClicked);

        UpdateCharCounter();
        SetSubmitInteractable(true);
        OnInputChanged(journalInputField ? journalInputField.text : string.Empty);
    }

    private void OnDestroy()
    {
        if (journalInputField)
            journalInputField.onValueChanged.RemoveListener(OnInputChanged);
        if (submitButton)
            submitButton.onClick.RemoveListener(OnSubmitClicked);
    }

    // ───────────── UI callbacks (no toggling here) ─────────────

    private void OnInputChanged(string _)
    {
        UpdateCharCounter();
        bool hasText = journalInputField && !string.IsNullOrWhiteSpace(journalInputField.text);
        SetSubmitInteractable(hasText);
    }

    public void OnSubmitClicked()
    {
        Debug.Log("[InGameJournal] OnSubmitClicked fired");
        if (!journalAPI)
        {
            Toast("API not available.");
            if (enableDebugLogs) Debug.LogError("[InGameJournal] JournalAPI reference not set on InGameJournal");
            return;
        }

        string text = journalInputField ? journalInputField.text : string.Empty;
        if (string.IsNullOrWhiteSpace(text))
        {
            Toast("Please enter something first.");
            return;
        }

        if (enableDebugLogs)
            Debug.Log($"[InGameJournal] Calling JournalAPI.SubmitJournalEntry ({text.Length} chars)");

        SetSubmitInteractable(false);

        // Submit and handle response
        journalAPI.SubmitJournalEntry(text, body =>
        {
            if (string.IsNullOrEmpty(body))
            {
                Toast("Submit failed");
                if (enableDebugLogs) Debug.LogWarning("[InGameJournal] Submit failed (null/empty body).");
            }
            else
            {
                Toast("Entry submitted.");
                if (enableDebugLogs) Debug.Log("[InGameJournal] Entry submitted. Response: " + body);

                if (journalInputField)
                    journalInputField.text = string.Empty;

                UpdateCharCounter();
            }

            SetSubmitInteractable(true);
        });
    }

    // ───────────── Helpers ─────────────

    private void UpdateCharCounter()
    {
        if (!characterCountText || !journalInputField) return;

        int len = journalInputField.text?.Length ?? 0;
        characterCountText.text = (maxCharacters > 0) ? $"{len}/{maxCharacters}" : $"{len}";
    }

    private void SetSubmitInteractable(bool canSubmit)
    {
        if (!submitButton) return;

        // toggle interactable, not component enable/disable
        submitButton.interactable = canSubmit;

        if (submitButton.targetGraphic)
            submitButton.targetGraphic.raycastTarget = true;
    }

    private void Toast(string msg)
    {
        if (toastText) toastText.text = msg;
        if (enableDebugLogs) Debug.Log($"[InGameJournal] {msg}");
    }

    // NO toggle code here. JournalPanelController owns opening/closing the panel.
}
