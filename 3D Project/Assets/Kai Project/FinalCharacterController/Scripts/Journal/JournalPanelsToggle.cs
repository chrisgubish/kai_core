using UnityEngine;
using UnityEngine.UI;

public class JournalPanelsToggle : MonoBehaviour
{
    [Header("Assign in Inspector")]
    public CanvasGroup journalPanel;       // JournalPanel CanvasGroup
    public CanvasGroup pastEntriesPanel;   // PastEntriesPanel CanvasGroup

    public JournalReader pastEntriesReader;

    void Awake()
    {
        // Start with Journal visible, Past hidden
        ShowJournal();
    }

    public void ShowJournal()
    {
        SetPanel(journalPanel, true);
        SetPanel(pastEntriesPanel, false);
        CursorManager.PushUI();
        if (journalPanel != null)
            journalPanel.transform.SetAsLastSibling();
    }

    public void ShowPast()
    {
        SetPanel(journalPanel, false);
        SetPanel(pastEntriesPanel, true);
        CursorManager.PushUI();

        if (pastEntriesPanel != null)
            pastEntriesPanel.transform.SetAsLastSibling();

        if (pastEntriesReader) pastEntriesReader.LoadPage();
    }

    private void SetPanel(CanvasGroup cg, bool on)
    {
        if (!cg) return;

        cg.alpha = on ? 1f : 0f;
        cg.interactable = on;
        cg.blocksRaycasts = on; // critical: off when hidden so it doesn't block clicks

        cg.gameObject.SetActive(true); // keep objects alive; alpha/raycast control interactivity
        Debug.Log($"[JournalPanelsToggle] SetPanel: {cg.name}, visible={on}, interactable={cg.interactable}, blocksRaycasts={cg.blocksRaycasts}");
    }
}
