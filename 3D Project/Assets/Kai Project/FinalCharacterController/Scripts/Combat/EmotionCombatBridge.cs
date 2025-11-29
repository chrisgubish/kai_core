using UnityEngine;
using System;
using System.Collections.Generic;

public class EmotionCombatBridge : MonoBehaviour
{
    [Header("Live inputs (set by your emotion source)")]
    [SerializeField] string primaryEmotion = "neutral";      // joy, anger, calm, fear, sad
    [SerializeField, Range(0,100)] int intensity = 0;        // 0–100
    [SerializeField, Range(-1f,1f)] float valence = 0f;      // -1..1
    [SerializeField, Range(0f,1f)] float arousal = 0.5f;     // 0..1

    [Header("Outputs (read by damage calc)")]
    [SerializeField] float attackMult = 1f;
    [SerializeField] float defenseMult = 1f;
    [SerializeField] float speedMult = 1f;
    [SerializeField] float critChanceAdd = 0f;               // +0..0.25

    public float AttackMult => attackMult;
    public float DefenseMult => defenseMult;
    public float SpeedMult => speedMult;
    public float CritChanceAdd => critChanceAdd;

    const float MIN_MULT = 0.5f;
    const float MAX_MULT = 1.5f;
    const float MAX_CRIT_ADD = 0.25f;

    static readonly Dictionary<string, Action<EmotionCombatBridge,float>> map =
        new Dictionary<string, Action<EmotionCombatBridge,float>>(StringComparer.OrdinalIgnoreCase) {
        // new(StringComparer.OrdinalIgnoreCase) {
        // scale = intensity [0..1]

        { "joy",   (b,s) => { b.attackMult=1f+0.20f*s;  b.speedMult=1f+0.20f*s;                        } },
        { "anger", (b,s) => { b.attackMult=1f+0.40f*s;  b.defenseMult=1f-0.20f*s; b.speedMult=1f+0.10f*s; } },
        { "calm",  (b,s) => { b.defenseMult=1f+0.25f*s; b.critChanceAdd=0f;         b.speedMult=1f-0.05f*s; } },
        { "fear",  (b,s) => {                          b.speedMult=1f+0.25f*s;      b.defenseMult=1f-0.15f*s; } },
        { "sad",   (b,s) => { b.attackMult=1f+0.20f*s;  b.defenseMult=1f-0.20f*s; b.critChanceAdd=0.10f*s; b.speedMult=1f-0.10f*s; } },
        };

    void ResetOutputs(){ attackMult=defenseMult=speedMult=1f; critChanceAdd=0f; }
    void ClampOutputs(){
        attackMult  = Mathf.Clamp(attackMult,  MIN_MULT, MAX_MULT);
        defenseMult = Mathf.Clamp(defenseMult, MIN_MULT, MAX_MULT);
        speedMult   = Mathf.Clamp(speedMult,   MIN_MULT, MAX_MULT);
        critChanceAdd = Mathf.Clamp(critChanceAdd, 0f, MAX_CRIT_ADD);
    }

    void Awake() { LoadLastEmotionIfEmpty(); Recompute(); }

    void SaveLastEmotion()
    {
        PlayerPrefs.SetString("emotion.primary", primaryEmotion);
        PlayerPrefs.SetInt ("emotion.intensity", intensity);
        PlayerPrefs.SetFloat ("emotion.valence",   valence);
        PlayerPrefs.SetFloat ("emotion.arousal",   arousal);
        PlayerPrefs.Save();
    }

    void LoadLastEmotionIfEmpty()
    {
        if (!string.IsNullOrEmpty(primaryEmotion)) return; // live feed or set in Inspector
        if (!PlayerPrefs.HasKey("emotion.primary")) return;

        primaryEmotion = PlayerPrefs.GetString("emotion.primary", "neutral");
        intensity      = PlayerPrefs.GetInt ("emotion.intensity", 0);
        valence        = PlayerPrefs.GetFloat ("emotion.valence",   0f);
        arousal        = PlayerPrefs.GetFloat ("emotion.arousal",   0.5f);
    }
    // Call SaveLastEmotion() whenever you change inputs from UI/editor to persist.

    public void SetEmotion(string emotion, int intensity01_100, float v, float a){
        primaryEmotion = string.IsNullOrEmpty(emotion) ? "neutral" : emotion;
        intensity = Mathf.Clamp(intensity01_100, 0, 100);
        valence = Mathf.Clamp(v, -1f, 1f);
        arousal = Mathf.Clamp01(a);
        Recompute();
        SaveLastEmotion();
    }

    // For event streams that pass intensity in 0..1
    public void OnEmotionChanged(string emotion, float intensity01, float v, float a){
        SetEmotion(emotion, Mathf.RoundToInt(Mathf.Clamp01(intensity01)*100f), v, a);
    }

    void Recompute(){
        ResetOutputs();
        float s = intensity / 100f;
        if (map.TryGetValue(primaryEmotion, out var apply)) apply(this, s);
        // unknown -> stays neutral (all 1.0 / 0.0)
        ClampOutputs();
    }

    #if UNITY_EDITOR
    // Re-run mapping whenever you edit fields in the Inspector (edit or play mode)
    void OnValidate()
    {
        Recompute();
        UnityEditor.EditorUtility.SetDirty(this);
    }

    // Optional: right-click the component header → “Recompute Now”
    [ContextMenu("Recompute Now")]
    void RecomputeNow() => Recompute();
    #endif


    void OnEnable(){
        // Seed from prior session if live stream not ready
        if (PlayerPrefs.HasKey("emotion.primary")){
            var e = PlayerPrefs.GetString("emotion.primary", "neutral");
            int i = PlayerPrefs.GetInt("emotion.intensity", 0);
            float v = PlayerPrefs.GetFloat("emotion.valence", 0f);
            float a = PlayerPrefs.GetFloat("emotion.arousal", 0.5f);
            SetEmotion(e,i,v,a);
        }
    }

    void OnDisable(){
        PlayerPrefs.SetString("emotion.primary", primaryEmotion);
        PlayerPrefs.SetInt("emotion.intensity", intensity);
        PlayerPrefs.SetFloat("emotion.valence", valence);
        PlayerPrefs.SetFloat("emotion.arousal", arousal);
        PlayerPrefs.Save();
    }

#if UNITY_EDITOR
    [ContextMenu("Run Spot Tests")]
    void RunSpotTests(){
        void Feed(string e, int i){ SetEmotion(e,i,0f,0.5f); }
        bool ok(bool cond, string name){ Debug.Log((cond?"PASS ":"FAIL ")+name); return cond; }

        Feed("anger",100); ok(Mathf.Approximately(AttackMult,1.4f) && DefenseMult < 1f, "anger@100 atk/def");
        Feed("calm",60);   ok(DefenseMult > 1f, "calm@60 def up");
        Feed("unknown",50);ok(Mathf.Approximately(AttackMult,1f) && Mathf.Approximately(DefenseMult,1f), "unknown neutral");
    }
#endif
}
