using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;
using UnityEngine.EventSystems;
using TMPro;
using UnityEngine.UI;
using UnityEngine.Networking;
using System;

public class JournalPanelController : MonoBehaviour
{
    [Header("UI")]
    [SerializeField] private GameObject journalPanel;
    [SerializeField] private TMP_InputField journalInput;
    [SerializeField] private TextMeshProUGUI charCounter;
    [SerializeField] private UnityJournalAPI journalAPI;     // assign in Inspector
    [SerializeField] private Transform entriesContainer;     // ScrollView/Viewport/Content
    [SerializeField] private GameObject journalEntryPrefab;  // the row prefab (with TMP_Text)
    [SerializeField] private GameObject noEntriesLabel;      // optional "No entries" text


    [Header("Input")]
    [Tooltip("PlayerControls action that toggles the journal (e.g., PlayerActionMap/ToggleJournal).")]
    [SerializeField] private InputActionReference toggleJournal;

    [Header("Behavior")]
    [SerializeField] private KeyCode fallbackToggleKey = KeyCode.J;
    [SerializeField] private bool startHidden = true;
    [SerializeField] private bool pauseGameWhenOpen = true;
    private bool _pausedByJournal = false;


    [Header("Wiring")]
    [SerializeField] private ScrollRect scrollRect;            // EntryScrollView
    [SerializeField] RectTransform contentRoot;                // your "Content" under the ScrollView
    [SerializeField] private GameObject emptyLabel;            // EmptyLabel text (optional)

    // fields somewhere near the top of the class
    [SerializeField] private int pageSize = 20;
    private int offset = 0;

    private InputAction _toggleAction;
    

    [Serializable]
    public class JournalListEntry
    {
        public string id;         // match your backend field names
        public string content;
        public string timestamp;  // ISO string from your API
    }

    private void OnEnable()
    {
        Debug.Log("[Journal] OnEnable start");
        if (toggleJournal == null || toggleJournal.action == null)
        {
            Debug.LogError("[Journal] Toggle action reference is NULL");
            return;
        }

        _toggleAction = toggleJournal.action;          // assign
        _toggleAction.actionMap?.Enable();             // enable map
        if (!_toggleAction.enabled) _toggleAction.Enable(); // enable action
        _toggleAction.performed += OnTogglePerformed;  // subscribe

        Debug.Log($"[Journal] Bound: action={_toggleAction.name}, map={_toggleAction.actionMap.name}, bind0={_toggleAction.bindings[0].effectivePath}, enabled={_toggleAction.enabled}");
    }

    private void OnDisable()
    {
        if (_toggleAction != null) _toggleAction.performed -= OnTogglePerformed;
    }

    private void Update()
    {
        // Fallback key (handy while wiring input)
        if (Input.GetKeyDown(fallbackToggleKey))
            TogglePanel();

        // live counter
        if (charCounter && journalInput && journalPanel && journalPanel.activeSelf)
            charCounter.text = $"{journalInput.text.Length}/2000";
    }

    private void OnTogglePerformed(InputAction.CallbackContext ctx)
    {
        // If panel is open AND the input field is focused, only allow Escape to toggle.
        Debug.Log($"[Journal] OnTogglePerformed phase={ctx.phase} control={ctx.control?.path}");
        if (journalPanel && journalPanel.activeSelf &&
            EventSystem.current != null &&
            EventSystem.current.currentSelectedGameObject == journalInput?.gameObject)
        {
            var key = ctx.control as KeyControl;
            if (key == null || key != Keyboard.current.escapeKey)
                return; // swallow J (and everything else) while typing
        }

        TogglePanel(); // your existing open/close logic
    }

    public void TogglePanel()
    {
        if (!journalPanel) return;
        // Toggle strictly via the unified setter
        bool show = !journalPanel.activeSelf || GetPanelAlpha() < 0.5f;
        SetPanelVisible(show);
    }

    private float GetPanelAlpha()
    {
        var cg = journalPanel ? journalPanel.GetComponent<CanvasGroup>() : null;
        return cg ? cg.alpha : (journalPanel && journalPanel.activeSelf ? 1f : 0f);
    }



    public void OpenPanel()  => SetPanelVisible(true);
    public void ClosePanel() => SetPanelVisible(false);

    private void SetPanelVisible(bool show)
    {
        if (!journalPanel)
        {
            Debug.LogWarning("[JournalPanelController] No journalPanel assigned.");
            return;
        }

        journalPanel.transform.SetAsLastSibling(); // keep on top

            // >>> always activate first when showing 
        if (show && !journalPanel.activeSelf)
        journalPanel.SetActive(true);

        var cg = journalPanel.GetComponent<CanvasGroup>();
        if (cg)
        {
            cg.alpha = show ? 1f : 0f;
            cg.interactable = show;
            cg.blocksRaycasts = show;
        }
        else
        {
            journalPanel.SetActive(show);
        }

        // // Cursor + UI navigation
        if (show) CursorManager.PushUI();
        else      CursorManager.PopUI();
        var es = UnityEngine.EventSystems.EventSystem.current;
        if (es) es.sendNavigationEvents = show;

        if (show)
        {
            journalInput?.ActivateInputField();
            if (charCounter && journalInput)
                charCounter.text = $"{journalInput.text.Length}/2000";
        }
        else
        {
            // onClose?.Invoke();
        }
        // --- Add pause/resume logic here ---
        if (pauseGameWhenOpen)
        {
            if (show && !_pausedByJournal)
            {
                Time.timeScale = 0f;
                _pausedByJournal = true;
                Debug.Log("[JournalPanelController] Game paused when journal opened.");
            }
            else if (!show && _pausedByJournal)
            {
                Time.timeScale = 1f;
                _pausedByJournal = false;
                Debug.Log("[JournalPanelController] Game unpaused when journal closed.");
            }
        }
    }


    public void LoadEntries()
    {
        // Panel may have been closed/destroyed: bail out early
        if (!isActiveAndEnabled || !gameObject)
            return;

        // Start with list cleared and the “no entries” label hidden
        if (emptyLabel) emptyLabel.SetActive(false);
        ClearList();

        // Request entries
        UnityJournalAPI.Instance.GetJournalEntries(pageSize, offset, entries =>
        {
            // If the panel was closed/destroyed while waiting for the web request, stop
            if (!this || !gameObject)
                return;

            // No data? show the “no entries” label
            if (entries == null || entries.Length == 0)
            {
                if (emptyLabel) emptyLabel.SetActive(true);
                return;
            }

            // Populate list
            foreach (var e in entries)
            {
                var go   = Instantiate(journalEntryPrefab, contentRoot);
                var body = go.transform.Find("Body")?.GetComponent<TMP_Text>();
                var ts   = go.transform.Find("Timestamp")?.GetComponent<TMP_Text>();

                if (body) body.text = e.content ?? "";
                if (ts)   ts.text   = string.IsNullOrEmpty(e.date_formatted) ? e.timestamp : e.date_formatted;
            }

            Canvas.ForceUpdateCanvases();
            if (scrollRect) scrollRect.verticalNormalizedPosition = 1f; // top
        });
    }

    public void NextPage()
    {
        offset += pageSize;
        LoadEntries();
    }
    public void PrevPage()
    {
        offset = Mathf.Max(0, offset - pageSize);
        LoadEntries();
    }


    private void ClearList()
    {
        if (!contentRoot) return;

        for (int i = contentRoot.childCount - 1; i >= 0; i--)
        {
            var child = contentRoot.GetChild(i).gameObject;

            // If this child IS the emptyLabel, skip it.
            if (emptyLabel && ReferenceEquals(child, emptyLabel))
                continue;

            Destroy(child);
        }
    }
}

