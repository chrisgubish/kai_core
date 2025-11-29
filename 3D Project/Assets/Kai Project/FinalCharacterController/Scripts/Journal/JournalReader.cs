using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System;

public class JournalReader : MonoBehaviour
{
    [Header("UI")]
    [SerializeField] private RectTransform listContent;     // ScrollRect Content
    [SerializeField] private GameObject entryItemPrefab;    // JournalEntryItem prefab
    [SerializeField] private Button loadButton;             // "Past Entries" button (optional)
    [SerializeField] private TMP_Text emptyLabel;           // shown when no entries

    [Header("Paging")]
    [SerializeField] 
    private int pageSize = 20;
    private int offset = 0;

    private RectTransform viewport;

    private void Awake()
    {
        if (loadButton) loadButton.onClick.AddListener(LoadPage);

        if (listContent != null)
        {
            viewport = listContent.parent as RectTransform;
            FixViewportSize();
        }

    }

    private void OnEnable()
    {
        FixViewportSize();
        // Auto load first page (optional)
        LoadPage();
    }
    
    private void FixViewportSize()
    {
        if (viewport != null)
        {
            // Force viewport to fill scroll view
            viewport.anchorMin = Vector2.zero;
            viewport.anchorMax = Vector2.one;
            viewport.offsetMin = Vector2.zero;
            viewport.offsetMax = Vector2.zero;
            viewport.sizeDelta = Vector2.zero;
            
            Debug.Log("[JournalReader] Fixed viewport size");

            if (listContent != null)
            {
                // Force content to fill viewport horizontally
                listContent.anchorMin = new Vector2(0, 1);
                listContent.anchorMax = new Vector2(1, 1);
                listContent.offsetMin = new Vector2(0, listContent.offsetMin.y);
                listContent.offsetMax = new Vector2(0, listContent.offsetMax.y);
                
                // Force immediate update
                Canvas.ForceUpdateCanvases();
                LayoutRebuilder.ForceRebuildLayoutImmediate(viewport);
                LayoutRebuilder.ForceRebuildLayoutImmediate(listContent);
                
                Debug.Log($"[JournalReader] Content width: {listContent.rect.width}, Viewport width: {viewport.rect.width}");
            }
        }
    }

    public void LoadPage()
    {
        if (UnityJournalAPI.Instance == null) { Debug.LogError("[JournalReader] API missing"); return; }

        // Clear current list visually
        for (int i = listContent.childCount - 1; i >= 0; i--) Destroy(listContent.GetChild(i).gameObject);
        if (emptyLabel) emptyLabel.gameObject.SetActive(false);

        UnityJournalAPI.Instance.GetJournalEntries(pageSize, offset, OnEntriesLoaded);
    }


    private void OnEntriesLoaded(UnityJournalAPI.JournalListEntry[] entries)
    {
        Debug.Log($"[JournalReader] OnEntriesLoaded called with {entries?.Length ?? 0} entries");
        
        if (entries == null || entries.Length == 0)
        {
            Debug.Log("[JournalReader] No entries to display");
            if (emptyLabel) emptyLabel.gameObject.SetActive(true);
            if (listContent)
            {
                for (int i = listContent.childCount - 1; i >= 0; i--)
                    Destroy(listContent.GetChild(i).gameObject);
            }
            return;
        }

        Debug.Log($"[JournalReader] Processing {entries.Length} entries");
        if (emptyLabel) emptyLabel.gameObject.SetActive(false);
        
        // Clear existing entries
        for (int i = listContent.childCount - 1; i >= 0; i--)
            Destroy(listContent.GetChild(i).gameObject);

        // Instantiate new entries
        foreach (var e in entries)
        {
            Debug.Log($"[JournalReader] Creating entry: {e.content?.Substring(0, Math.Min(50, e.content?.Length ?? 0))}...");
            
            var go = Instantiate(entryItemPrefab, listContent);
            Debug.Log($"[JournalReader] Instantiated prefab, active: {go.activeSelf}");
            
            // Wire texts
            var body = go.transform.Find("InnerLayout/Body")?.GetComponent<TMP_Text>();
            var ts   = go.transform.Find("InnerLayout/Timestamp")?.GetComponent<TMP_Text>();

            Debug.Log($"[JournalReader] Found Body: {body != null}, Found Timestamp: {ts != null}");
            
            if (body) 
            {
                body.text = string.IsNullOrEmpty(e?.content) ? "(no content)" : e.content;
                Debug.Log($"[JournalReader] Set body text to: {body.text.Substring(0, Math.Min(50, body.text.Length))}...");
            }
            
            if (ts) 
            {
                ts.text = !string.IsNullOrEmpty(e.date_formatted) ? e.date_formatted :
                        (!string.IsNullOrEmpty(e.timestamp) ? e.timestamp : "");
                Debug.Log($"[JournalReader] Set timestamp to: {ts.text}");
            }
        }        
        
        Debug.Log($"[JournalReader] Content now has {listContent.childCount} children");

        FixViewportSize();
        

        Canvas.ForceUpdateCanvases();
        LayoutRebuilder.ForceRebuildLayoutImmediate(listContent);
    }

    public void NextPage() { offset += pageSize; LoadPage(); }
    public void PrevPage() { offset = Mathf.Max(0, offset - pageSize); LoadPage(); }
}
