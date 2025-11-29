#if UNITY_EDITOR || DEVELOPMENT_BUILD


using System;
using UnityEngine;
using UnityEngine.EventSystems;

public class MoodPointUI : MonoBehaviour,
    IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler
{
    public Action<MoodPointUI, Vector2> Hover;
    public Action<MoodPointUI> Exit;
    public event Action<MoodPointUI> Down;

    public EmotionPoint data;   // your payload (emotion, intensity, time, etc.)
    public bool isPinned;       // toggled by the controller

    public void OnPointerEnter(PointerEventData e)
    {
        var rt = (RectTransform)transform;
        Hover?.Invoke(this, rt.anchoredPosition);
    }

    public void OnPointerExit(PointerEventData e) => Exit?.Invoke(this);

    public void OnPointerDown(PointerEventData e) => Down?.Invoke(this);
}


// using UnityEngine;
// using UnityEngine.EventSystems;
// using System;

// public class MoodPointUI : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler
//  {
//     public System.Action<MoodPointUI, Vector2> Hover;
//     public System.Action<MoodPointUI> Exit;
//     public event System.Action<MoodPointUI> Down;

//     // public event System.Action<MoodPointUI> Click;

//     // Carry whatever your point data class is called:
//     public EmotionPoint data; // valence, arousal, intensity, timestamp, primary_emotion

//     public bool isPinned;

//     public void OnPointerEnter(PointerEventData e) {
//         var rt = (RectTransform)transform;
//         Hover?.Invoke(this, rt.anchoredPosition);
//     }

//     private bool isPinned = false;




//     private IEnumerator FadeTooltip(bool show)
//     {
//         CanvasGroup cg = GetComponent<CanvasGroup>();
//         float targetAlpha = show ? 1f : 0f;
//         while (!Mathf.Approximately(cg.alpha, targetAlpha))
//         {
//             cg.alpha = Mathf.MoveTowards(cg.alpha, targetAlpha, Time.deltaTime * 5f);
//             yield return null;
//         }
//     }

//     StartCoroutine(FadeTooltip(true));   // Fade in
//     StartCoroutine(FadeTooltip(false));  // Fade out


//     public void OnPointerExit(PointerEventData e) => Exit?.Invoke(this);

//     public void OnPointerDown(PointerEventData e) => Down?.Invoke(this);
//     {
//         isPinned = !isPinned;  // Toggle
//         if (isPinned)
//             ShowTooltip();
//         else
//             HideTooltip();
//     }


//     // public void OnPointerClick(UnityEngine.EventSystems.PointerEventData eventData)
//     // {
//     //     isPinned = !isPinned;
//     //     onClick?.Invoke(this);
//     // }

//     // public void OnPointerClick(PointerEventData e) => Click?.Invoke(this);
// }

#endif