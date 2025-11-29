#if UNITY_EDITOR || DEVELOPMENT_BUILD

using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

[Serializable]
public class EmotionPoint {
    public DateTime timestamp;
    public string primary_emotion;
    public float valence;   // -1..1
    public float arousal;   // 0..1
    public float intensity; // 0..100 (optional)
}

public class MoodMapController : MonoBehaviour
{
    [Header("Refs")]
    public RectTransform plotArea;     // panel rect
    public RectTransform pointsParent; // usually same as plotArea
    public GameObject moodPointPrefab; // the small dot prefab

    [Header("HUD")]
    [SerializeField] private RectTransform hudRoot; // assign hudRoot in Inspector
    [SerializeField] private GameObject hudPrefab;  // assign MoodPointHUD prefab 

    [Header("HUD Timing")]
    [SerializeField] private float hudFadeIn = 0.12f;
    [SerializeField] private float hudFadeOut = 0.12f;
    [SerializeField] private float hudHideDelay = 0.15f;

    [Header("Emotion Colors")]
    [SerializeField] private Color defaultColor = Color.white;
    [SerializeField] private Color angerColor   = Color.red;
    [SerializeField] private Color joyColor     = Color.yellow;
    [SerializeField] private Color calmColor    = new Color(0.4f, 0.6f, 1f); // soft blue
    [SerializeField] private Color sadnessColor = new Color(0.2f, 0.3f, 0.8f);
    [SerializeField] private Color fearColor    = new Color(0.5f, 0.2f, 0.7f);


    // runtime
    private Coroutine hudFadeCo;
    private Coroutine hudHideCo;


    [Header("Visuals")]
    public float pointSize = 8f;

    //runtime HUD state
    private GameObject hud;
    private CanvasGroup hudCg;
    private RectTransform hudRt;
    private TMPro.TMP_Text hudTitle, hudMeta;

    private readonly List<GameObject> spawned = new List<GameObject>();

    private void ClearPoints() {
        for (int i = 0; i < spawned.Count; i++) Destroy(spawned[i]);
        spawned.Clear();
    }

    // Map valence [-1..1] → X, arousal [0..1] → Y
    private Vector2 ToLocal(float valence, float arousal) {
        // Safety clamp (redundant with the caller, but harmless)
        valence = Mathf.Clamp(valence, -1f, 1f);
        arousal = Mathf.Clamp01(arousal);
        
        float w = plotArea.rect.width;
        float h = plotArea.rect.height;

        // Map: v=-1 → x=0, v=+1 → x=w
        float x = (valence + 1f) * 0.5f * w;  // -1→0, +1→w
        // Map: a=0 → y=0, a=1 → y=h
        float y = arousal * h;               // 0→0, 1→h
        
        return new Vector2(x, y);
    }

    private Color GetColorForEmotion(string emotion)
    {
        if (string.IsNullOrEmpty(emotion)) return defaultColor;

        emotion = emotion.ToLowerInvariant();
        if (emotion.Contains("anger") || emotion.Contains("rage")) return angerColor;
        if (emotion.Contains("joy")   || emotion.Contains("happy")) return joyColor;
        if (emotion.Contains("calm")  || emotion.Contains("peace")) return calmColor;
        if (emotion.Contains("sad")   || emotion.Contains("grief")) return sadnessColor;
        if (emotion.Contains("fear")  || emotion.Contains("anx"))  return fearColor;

        return defaultColor;
    }

    private MoodPointUI pinned;          // the currently pinned point (or null)
    private Color pinnedHighlight = Color.white; // optional: highlight color

    public void RenderPoints(List<EmotionPoint> pts)
    {
        // 0) Hard guards: if the UI references are missing, bail out safely.
        if (plotArea == null) {
            Debug.LogWarning("[MoodMap] RenderPoints aborted: plotArea is null");
            return;
        }
        if (pointsParent == null) {
            Debug.LogWarning("[MoodMap] RenderPoints aborted: pointsParent is null");
            return;
        }
        if (moodPointPrefab == null) {
            Debug.LogWarning("[MoodMap] RenderPoints aborted: moodPointPrefab is null");
            return;
        }

        // 1) Start fresh
        ClearPoints();

        // 2) If there’s no data, we’re done (no error)
        if (pts == null || pts.Count == 0) {
            // Optional: show a "No data" label here.
            return;
        }

        // 3) Optional cap to avoid too many UI objects (performance)
        const int MAX_POINTS = 500;
        int count = Mathf.Min(pts.Count, MAX_POINTS);

        // 4) Plot each point safely
        for (int i = 0; i < count; i++) {
            EmotionPoint p = pts[i];
            if (p == null) continue;

            // 4a) Skip invalid numbers (NaN = Not a Number). NaN breaks math/positioning.
            if (float.IsNaN(p.valence) || float.IsNaN(p.arousal)) {
                Debug.LogWarning($"[MoodMap] Skipping NaN sample at index {i}");
                continue;
            }

            // 4b) Clamp to valid input ranges
            // valence must be within [-1..1], arousal within [0..1].
            float v = Mathf.Clamp(p.valence, -1f, 1f);
            float a = Mathf.Clamp01(p.arousal);

            // 4c) Convert (v,a) to local pixel position inside plotArea
            Vector2 local = ToLocal(v, a);  // this should already map 0..width, 0..height

            // 4d) Extra safety: clamp to panel rect so we never place outside
            Rect r = plotArea.rect;
            local.x = Mathf.Clamp(local.x, 0f, r.width);
            local.y = Mathf.Clamp(local.y, 0f, r.height);

            // 4e) Spawn the dot
            GameObject go = Instantiate(moodPointPrefab, pointsParent);
            spawned.Add(go);

            var ui = go.GetComponent<MoodPointUI>() ?? go.AddComponent<MoodPointUI>();
            ui.data = p; // your EmotionPoint for this dot


            // Unsubscribe first to avoid duplicates
            ui.Hover -= OnPointHover;
            ui.Exit  -= OnPointExit;
            ui.Down  -= OnPointDown;

            // Subscribe
            ui.Hover += OnPointHover;
            ui.Exit  += OnPointExit;
            ui.Down  += OnPointDown;


            // //Unsubscribe first to avoid duplicates
            // ui.Hover -= OnPointHover; ui.Exit -= OnPointExit;
            // ui.Down -= OnPointDown; ui.Click -= OnPointClick;

            // //Subscribe
            // ui.Hover += OnPointHover; ui.Exit += OnPointExit;
            // ui.Down += OnPointDown; ui.Click += OnPointClick;


            void OnPointHover(MoodPointUI point, Vector2 localPos)
            {
                if (pinned != null && pinned != point) return;

                EnsureHud();

                // 1) Text formatting: short, local time
                var ts = point.data.timestamp.ToLocalTime();
                hudTitle.text = point.data.primary_emotion?.ToLowerInvariant();
                hudMeta.text  = $"{ts:g}  •  Int {(int)point.data.intensity}%";

                // 2) Position near dot with offset, clamped to plot area
                Vector2 target = localPos + new Vector2(12, 12);
                var r = plotArea.rect;
                target.x = Mathf.Clamp(target.x, 0, r.width);
                target.y = Mathf.Clamp(target.y, 0, r.height);
                hudRt.anchoredPosition = target;

                // 3) Cancel any pending hide
                if (hudHideCo != null) { StopCoroutine(hudHideCo); hudHideCo = null; }
                
                // Change HUD background color to match emotion
                var bg = hud.GetComponent<UnityEngine.UI.Image>();
                if (bg)
                {
                    var c = GetColorForEmotion(point.data.primary_emotion);
                    c.a = 0.75f; // semi-transparent panel
                    bg.color = c;
                }

                // 4) Show + fade in (only if not already visible)
                hud.SetActive(true);
                if (hudFadeCo != null) StopCoroutine(hudFadeCo);
                hudFadeCo = StartCoroutine(FadeCanvasGroup(hudCg, hudCg.alpha, 1f, hudFadeIn));
            }

            // void OnPointClick(MoodPointUI point)
            // {
            //     // Toggle this point's pinned state
            //     bool willPin = !point.isPinned;

            //     // Unpin old (if any) when switching to a new pin
            //     if (willPin && pinned != null && pinned != point)
            //         UnpinCurrent();

            //     point.isPinned = willPin;

            //     if (willPin)
            //     {
            //         pinned = point;

            //         // Keep HUD visible and solid
            //         if (hudHideCo != null) StopCoroutine(hudHideCo);
            //         if (hudFadeCo != null) StopCoroutine(hudFadeCo);
            //         if (hud) { hud.SetActive(true); hudCg.alpha = 1f; }

            //         // Optional: highlight pinned point
            //         var img = point.GetComponent<UnityEngine.UI.Image>();
            //         if (img) img.color = pinnedHighlight;

            //         // Ensure HUD shows info for the pinned point immediately
            //         OnPointHover(point, ((RectTransform)point.transform).anchoredPosition);
            //     }
            //     else
            //     {
            //         // Unpin same point
            //         UnpinCurrent();

            //         // Return to normal hide behavior (delayed fade-out)
            //         if (hudHideCo != null) StopCoroutine(hudHideCo);
            //         hudHideCo = StartCoroutine(HideHudAfterDelay());
            //     }
            // }

            void UnpinCurrent()
            {
                if (pinned == null) return;

                // Restore color based on emotion + intensity
                var img = pinned.GetComponent<UnityEngine.UI.Image>();
                if (img)
                {
                    var baseCol = GetColorForEmotion(pinned.data.primary_emotion);
                    float alpha = Mathf.Clamp01(pinned.data.intensity / 100f);
                    img.color = new Color(baseCol.r, baseCol.g, baseCol.b, Mathf.Lerp(0.6f, 1f, alpha));
                }

                pinned.isPinned = false;
                pinned = null;
            }




            void OnPointDown(MoodPointUI point)
            {
                bool willPin = !point.isPinned;

                if (willPin && pinned != null && pinned != point)
                    UnpinCurrent();

                point.isPinned = willPin;

                if (willPin)
                {
                    pinned = point;

                    if (hudHideCo != null) { StopCoroutine(hudHideCo); hudHideCo = null; }
                    if (hudFadeCo != null) { StopCoroutine(hudFadeCo); hudFadeCo = null; }

                    EnsureHud();
                    hud.SetActive(true);
                    hudCg.alpha = 1f;

                    // optional highlight
                    var img = point.GetComponent<UnityEngine.UI.Image>();
                    if (img) img.color = pinnedHighlight;

                    // refresh HUD content/position
                    var localPos = ((RectTransform)point.transform).anchoredPosition;
                    OnPointHover(point, localPos);
                }
                else
                {
                    UnpinCurrent();
                    if (hudHideCo != null) StopCoroutine(hudHideCo);
                    hudHideCo = StartCoroutine(HideHudAfterDelay());
                }
            }


            // void OnPointDown(MoodPointUI point)
            // {
            //     // Toggle pin early (before exit runs)
            //     bool willPin = !point.isPinned;

            //     if (willPin && pinned != null && pinned != point)
            //         UnpinCurrent();

            //     point.isPinned = willPin;

            //     if (willPin)
            //     {
            //         pinned = point;

            //         // Keep HUD solid and visible
            //         if (hudHideCo != null) { StopCoroutine(hudHideCo); hudHideCo = null; }
            //         if (hudFadeCo != null) { StopCoroutine(hudFadeCo); hudFadeCo = null; }
            //         EnsureHud();
            //         hud.SetActive(true);
            //         hudCg.alpha = 1f;

            //         // Optional: highlight pinned point
            //         var img = point.GetComponent<UnityEngine.UI.Image>();
            //         if (img) img.color = pinnedHighlight;

            //         // Make sure HUD shows correct info immediately
            //         var localPos = ((RectTransform)point.transform).anchoredPosition;
            //         OnPointHover(point, localPos); // updates text/position but won't fade since alpha=1
            //     }
            //     else
            //     {
            //         // Unpin same point; allow normal hide behavior
            //         UnpinCurrent();
            //         if (hudHideCo != null) StopCoroutine(hudHideCo);
            //         hudHideCo = StartCoroutine(HideHudAfterDelay());
            //     }
            // }


            // void OnPointClick(MoodPointUI point)
            // {
            //     if (point.isPinned)
            //     {
            //         // Keep HUD visible
            //         if (hudHideCo != null) StopCoroutine(hudHideCo);
            //         if (hudFadeCo != null) StopCoroutine(hudFadeCo);
            //         hudCg.alpha = 1f;
            //     }
            //     else
            //     {
            //         // Return to normal hide behavior
            //         if (hudHideCo != null) StopCoroutine(hudHideCo);
            //         hudHideCo = StartCoroutine(HideHudAfterDelay());
            //     }

            //     // Optional: highlight pinned point
            //     var img = point.GetComponent<UnityEngine.UI.Image>();
            //     if (img)
            //         img.color = point.isPinned ? Color.white : GetColorForEmotion(point.data.primary_emotion);
            // }



            void OnPointExit(MoodPointUI point)
            {
                if (pinned == point) return;

                // Delay a bit, then fade out and disable
                if (!hud) return;
                if (hudHideCo != null) StopCoroutine(hudHideCo);
                hudHideCo = StartCoroutine(HideHudAfterDelay());
            }


            // void OnPointHover(MoodPointUI point, Vector2 localPos) {
            //     EnsureHud();
            //     hudTitle.text = point.data.primary_emotion;
            //     hudMeta.text  = $"{point.data.timestamp:G}  •  Int {(int)point.data.intensity}%";
            //     hud.SetActive(true);
            //     hudCg.alpha = 1f;

            //     // Offset + clamp inside plot
            //     Vector2 target = localPos + new Vector2(12, 12);
            //     var r = plotArea.rect;
            //     target.x = Mathf.Clamp(target.x, 0, r.width);
            //     target.y = Mathf.Clamp(target.y, 0, r.height);
            //     hudRt.anchoredPosition = target;
            // }

            // void OnPointExit(MoodPointUI point) {
            //     HideHud();
            // }

            // Ensure it's really a UI element
            RectTransform rt = go.transform as RectTransform;
            if (rt == null) {
                Debug.LogWarning("[MoodMap] moodPointPrefab is not a UI (RectTransform) object. Please use a UI Image prefab.");
                Destroy(go);
                continue;
            }

            // Size and place the dot
            float size = Mathf.Max(1f, pointSize); // avoid zero or negative
            rt.sizeDelta = new Vector2(size, size);
            rt.anchorMin = rt.anchorMax = new Vector2(0f, 0f); // bottom-left
            rt.pivot = new Vector2(0.5f, 0.5f);               // center the dot on the position
            rt.anchoredPosition = local;
            go.transform.SetAsLastSibling();                    // ensure above bg


            var img = go.GetComponent<UnityEngine.UI.Image>();
            if (img) {
                Color baseCol = GetColorForEmotion(p.primary_emotion);
                float alpha = Mathf.Clamp01(p.intensity / 100f);
                img.color = new Color(baseCol.r, baseCol.g, baseCol.b, Mathf.Lerp(0.6f, 1f, alpha));
            }
                // img.raycastTarget = true;                  // belt-and-suspenders
                // if (intensityGradient != null)
                //     img.color = intensityGradient.Evaluate(Mathf.Clamp01(p.intensity / 100f));

            // OPTIONAL: color by intensity if you’ve added a Gradient
            // var img = go.GetComponent<Image>();
            // if (img && intensityGradient != null)
            //     img.color = intensityGradient.Evaluate(Mathf.Clamp01(p.intensity / 100f));
        }
    }

    private IEnumerator FadeCanvasGroup(CanvasGroup cg, float from, float to, float duration, System.Action onDone = null)
    {
        float t = 0f;
        cg.alpha = from;
        while (t < duration)
        {
            t += Time.unscaledDeltaTime;          // use unscaled so it works when paused
            float k = duration > 0f ? t / duration : 1f;
            cg.alpha = Mathf.Lerp(from, to, k);
            yield return null;
        }
        cg.alpha = to;
        onDone?.Invoke();
    }

    private IEnumerator HideHudAfterDelay()
    {
        yield return new WaitForSecondsRealtime(hudHideDelay);
        if (hudFadeCo != null) StopCoroutine(hudFadeCo);
        hudFadeCo = StartCoroutine(FadeCanvasGroup(hudCg, hudCg.alpha, 0f, hudFadeOut, () =>
        {
            if (hud) hud.SetActive(false);
        }));
    }


    void EnsureHud() {
    if (hud) return;
    hud = Instantiate(hudPrefab, hudRoot);
    hudRt = (RectTransform)hud.transform;
    hudTitle = hud.transform.Find("Title").GetComponent<TMPro.TMP_Text>();
    hudMeta  = hud.transform.Find("Meta").GetComponent<TMPro.TMP_Text>();
    hudCg    = hud.GetComponent<CanvasGroup>();
    hud.SetActive(false);
    }
    void HideHud() { if (hud) hud.SetActive(false); }


    public Gradient intensityGradient;

    // public void RenderPoints(List<EmotionPoint> pts) {
    //     ClearPoints();
    //     if (pts == null) return;
    //     foreach (var p in pts) {
    //         var go = Instantiate(moodPointPrefab, pointsParent);
    //         var rt = (RectTransform)go.transform;
    //         rt.sizeDelta = new Vector2(pointSize, pointSize);
    //         rt.anchoredPosition = ToLocal(p.valence, p.arousal);
    //         spawned.Add(go);
    //     }

    // void Update() {
    // if (Input.GetKeyDown(KeyCode.F9))
    //     hudRoot.gameObject.SetActive(!hudRoot.gameObject.activeSelf);
    // }
}

#endif