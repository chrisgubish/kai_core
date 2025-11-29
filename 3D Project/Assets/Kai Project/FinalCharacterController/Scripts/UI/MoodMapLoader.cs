#if UNITY_EDITOR || DEVELOPMENT_BUILD

using System;
using System.Collections.Generic;
using UnityEngine;

public class MoodMapLoader : MonoBehaviour
{
    public MoodMapController controller;
    public int days = 7;

    void Start() {
        UnityJournalAPI.Instance.GetMoodSamples(days, dtos =>
        {
            if (dtos == null) { controller.RenderPoints(null); return; }
            var list = new List<EmotionPoint>(dtos.Length);
            foreach (var d in dtos) {
                DateTime ts; DateTime.TryParse(d.timestamp, out ts);
                list.Add(new EmotionPoint {
                    timestamp = ts,
                    primary_emotion = d.primary_emotion,
                    valence = d.valence,
                    arousal = d.arousal,
                    intensity = d.intensity
                });
            }
            controller.RenderPoints(list);
        });
    }
}

#endif